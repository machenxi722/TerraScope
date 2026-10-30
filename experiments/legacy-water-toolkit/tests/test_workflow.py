import json
import sys

import numpy as np
import pytest
import torch

from tsft import evaluate, train
from tsft.common import atomic_torch_save, sha256, write_json
from tsft.dataset import CachedDataset
from tsft.head import WaterHead


def make_fixture(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    samples = []
    for i, split in enumerate(("train", "train", "val", "test")):
        name = f"synthetic_{i}"
        target = tmp_path / f"{name}.npz"
        label = np.zeros((16, 16), np.uint8)
        if i != 1:
            label[4:12, 4:12] = 1
        np.savez_compressed(target, label=label, valid=np.ones_like(label), area_m2=np.ones_like(label)*100.)
        samples.append({"id": name, "split": split, "target": target.name, "image": "unused.png",
                        "target_sha256": sha256(target), "crs": "EPSG:32631",
                        "transform": [10, 0, 500000, 0, -10, 1000000]})
    manifest = tmp_path / "manifest.json"
    write_json(manifest, {"dataset": "synthetic-test-fixture", "samples": samples})
    metadata = {"fingerprint": "fixture", "protocol": "synthetic", "manifest_sha256": sha256(manifest)}
    head = WaterHead(llm_dim=32, grid=4)
    head.save_base(cache / "base_head.pt", metadata)
    index = {"fingerprint": "fixture", "metadata": metadata, "complete": True,
             "base_sha256": sha256(cache / "base_head.pt"), "features": {}}
    for row in samples:
        path = cache / f"{row['id']}.pt"
        atomic_torch_save({"id": row["id"], "fingerprint": "fixture", "seg_hidden": torch.randn(1, 32),
                          "raw_fpn": [torch.randn(1, 256, s, s) for s in (16, 8, 4)]}, path)
        index["features"][row["id"]] = {"file": path.name, "sha256": sha256(path), "split": row["split"]}
    write_json(cache / "index.json", index)
    return manifest, cache


def test_real_training_entrypoint_and_geotiff_evaluation(tmp_path, monkeypatch):
    manifest, cache = make_fixture(tmp_path)
    out = tmp_path / "M2"
    monkeypatch.setattr(sys, "argv", ["train", "--manifest", str(manifest), "--cache", str(cache),
                      "--out", str(out), "--device", "cpu", "--max-steps", "2", "--val-every", "1",
                      "--accum", "2", "--area-weight", "0.1"])
    train.main()
    status = json.loads((out / "status.json").read_text())
    assert status["last_step"] == 2 and (out / "best.pt").exists()
    destination = tmp_path / "eval"
    monkeypatch.setattr(sys, "argv", ["evaluate", "--manifest", str(manifest), "--cache", str(cache),
                      "--out", str(destination), "--device", "cpu", "--split", "test",
                      "--checkpoint", str(out / "best.pt"), "--export-masks"])
    evaluate.main()
    summary = json.loads((destination / "summary.json").read_text())
    assert summary["n"] == 1 and summary["split"] == "test"
    import rasterio
    with rasterio.open(destination / "masks/synthetic_3.tif") as tif:
        assert tif.nodata == 255 and tif.crs.to_epsg() == 32631 and tif.shape == (16, 16)


def test_stale_or_incomplete_cache_fails_closed(tmp_path):
    manifest, cache = make_fixture(tmp_path)
    CachedDataset(manifest, cache, "train")
    index_path = cache / "index.json"
    index = json.loads(index_path.read_text())
    index["complete"] = False
    write_json(index_path, index)
    with pytest.raises(ValueError, match="Incomplete"):
        CachedDataset(manifest, cache, "train")
    index["complete"] = True
    index["features"]["synthetic_0"]["split"] = "test"
    write_json(index_path, index)
    with pytest.raises(ValueError, match="Split changed"):
        CachedDataset(manifest, cache, "train")


def test_raster_preparation_band_order_invalid_and_geometry(tmp_path, monkeypatch):
    import rasterio
    from affine import Affine
    from PIL import Image
    from tsft import data
    raw = tmp_path / "raw"
    raw.mkdir()
    profile = dict(driver="GTiff", width=4, height=4, crs="EPSG:4326",
                   transform=Affine(.0001, 0, 0, 0, -.0001, 60), dtype="int16")
    bands = np.zeros((13, 4, 4), dtype=np.int16)
    bands[3], bands[2], bands[1] = 3000, 2000, 1000
    with rasterio.open(raw / "A_S2Hand.tif", "w", count=13, **profile) as dst:
        dst.write(bands)
    label = np.zeros((4, 4), dtype=np.int16)
    label[0, 0], label[1, 1] = -1, 1
    with rasterio.open(raw / "A_LabelHand.tif", "w", count=1, **profile) as dst:
        dst.write(label, 1)
    monkeypatch.setattr(data, "official_rows", lambda: [{"id": "A", "split": "train",
                       "s2": "A_S2Hand.tif", "label": "A_LabelHand.tif"}])
    output = tmp_path / "prepared"
    result = data.build_manifest(raw, output)
    assert result["samples"][0]["valid_pixels"] == 15
    np.testing.assert_array_equal(np.asarray(Image.open(output / "rgb/A.png"))[0, 0], [255, 170, 85])
    with np.load(output / "targets/A.npz") as target:
        assert target["valid"][0, 0] == 0 and target["label"][1, 1] == 1
        assert 50 < target["area_m2"].mean() < 70
    with rasterio.open(raw / "A_LabelHand.tif", "r+") as dst:
        dst.transform = Affine(.0001, 0, .001, 0, -.0001, 60)
    with pytest.raises(ValueError, match="geometry mismatch"):
        data.build_manifest(raw, tmp_path / "bad_geometry")
