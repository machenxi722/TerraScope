"""Real-GPU pilot: frozen feature parity is checked by cache; check backward and reload here."""
import argparse
import time
from pathlib import Path

import numpy as np
import torch

from .cache import amp
from .common import (atomic_torch_save, check_deadline, deadline, load_manifest,
                     load_tensor_file, read_json, sha256, write_json)
from .dataset import to_device
from .head import WaterHead, losses, native_logits


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", required=True)
    p.add_argument("--cache", required=True, help="Can be the incomplete two-image pilot cache")
    p.add_argument("--out", required=True)
    p.add_argument("--hours", type=float, default=.25)
    a = p.parse_args()
    end, start = deadline(a.hours), time.time()
    cache = Path(a.cache)
    index = read_json(cache / "index.json")
    if index["metadata"]["manifest_sha256"] != sha256(a.manifest):
        raise ValueError("Manifest changed")
    rows = {r["id"]: r for r in load_manifest(a.manifest)["samples"]}
    entries = [(k, v) for k, v in index["features"].items() if v["split"] == "train"][:2]
    if not entries:
        raise ValueError("Pilot needs at least one training image")
    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
        raise RuntimeError("CUDA BF16 required")
    torch.cuda.reset_peak_memory_stats()
    head, meta = WaterHead.load_base(cache / "base_head.pt")
    head.cuda().train()
    optimizer = torch.optim.AdamW([p for p in head.parameters() if p.requires_grad], lr=1e-5)
    measured = []
    for sample_id, entry in entries:
        check_deadline(end)
        feature = load_tensor_file(cache / entry["file"])
        with np.load(rows[sample_id]["target"], allow_pickle=False) as z:
            target = {k: torch.from_numpy(z[k].copy())[None, None] for k in ("label", "valid", "area_m2")}
        feature, target = to_device(feature, target, "cuda")
        optimizer.zero_grad(set_to_none=True)
        with amp("cuda"):
            low, ious = head(feature["raw_fpn"], feature["seg_hidden"])
            loss, _ = losses(native_logits(low, target["label"].shape[-2:]), ious,
                              target["label"], target["valid"], target["area_m2"], .1)
        loss.backward()
        for module in (head.projector, head.decoder.conv_s0, head.decoder.conv_s1):
            assert any(p.grad is not None and bool(p.grad.abs().sum() > 0) for p in module.parameters())
        torch.nn.utils.clip_grad_norm_(head.parameters(), 1.0, error_if_nonfinite=True)
        optimizer.step()
        measured.append(float(loss))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    head.eval()
    with torch.no_grad(), amp("cuda"):
        before = head(feature["raw_fpn"], feature["seg_hidden"])[0].cpu()
    head.save_base(out / "reload_check.pt", meta)
    restored, _ = WaterHead.load_base(out / "reload_check.pt")
    restored.cuda().eval()
    with torch.no_grad(), amp("cuda"):
        after = restored(feature["raw_fpn"], feature["seg_hidden"])[0].cpu()
    torch.testing.assert_close(before, after, rtol=0, atol=0)
    write_json(out / "preflight.json", {"passed": True, "real_training_images": len(entries),
               "losses": measured, "seconds": time.time() - start,
               "head_peak_gpu_gib": torch.cuda.max_memory_allocated() / 2**30,
               "cache_peak_gpu_gib": index.get("peak_gpu_gib"), "official_head_parity": index.get("parity"),
               "gpu": torch.cuda.get_device_name(), "reload_max_abs_diff": float((before-after).abs().max()),
               "note": "Pilot weights are discarded. M1 and M2 both initialize from untouched base_head.pt."})
    print("GPU preflight passed. Pilot weights are not experiment weights.")


if __name__ == "__main__":
    main()
