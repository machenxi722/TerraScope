"""Build a split-locked Sen1Floods11 manifest; no label-derived RGB operations."""
import argparse
import csv
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from pyproj import CRS, Geod

from .common import ROOT, sha256, verify_sources, write_json

SPLIT_FILES = {"train": "train", "val": "valid", "test": "test", "bolivia": "bolivia"}


def official_rows():
    verify_sources()
    rows = []
    for split, filename in SPLIT_FILES.items():
        with open(ROOT / "splits" / f"flood_{filename}_data.csv") as f:
            for s1, label in csv.reader(f):
                sample_id = label.removesuffix("_LabelHand.tif")
                rows.append({"id": sample_id, "split": split,
                             "s2": s1.replace("_S1Hand.tif", "_S2Hand.tif"), "label": label})
    assert len({r["id"] for r in rows}) == len(rows) == 446
    return rows


def pixel_areas(crs, transform, height, width):
    """m²: ellipsoidal row areas for north-up lon/lat; planar units for projected CRS."""
    crs = CRS.from_user_input(crs)
    if crs.is_geographic:
        if transform.b != 0 or transform.d != 0 or crs.to_epsg() != 4326:
            raise ValueError("Geographic area requires unrotated EPSG:4326; reproject explicitly first")
        geod = Geod(ellps="WGS84")
        areas = []
        for y in range(height):
            x0, y0 = transform * (0, y)
            x1, y1 = transform * (1, y + 1)
            area, _ = geod.polygon_area_perimeter([x0, x1, x1, x0], [y0, y0, y1, y1])
            areas.append(abs(area))
        result = np.broadcast_to(np.asarray(areas)[:, None], (height, width)).copy()
    elif crs.is_projected:
        factors = [a.unit_conversion_factor for a in crs.axis_info[:2]]
        if len(factors) != 2:
            raise ValueError("Unknown projected CRS units")
        area = abs(transform.a * transform.e - transform.b * transform.d) * factors[0] * factors[1]
        result = np.full((height, width), area, dtype=np.float64)
    else:
        raise ValueError("Unsupported CRS")
    if not np.all(np.isfinite(result) & (result > 0)):
        raise ValueError("Invalid pixel area")
    return result.astype(np.float32)


def build_manifest(raw, out, reflectance_max=0.3):
    raw, out = Path(raw).resolve(), Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    index = {}
    for path in raw.rglob("*.tif"):
        if path.name in index:
            raise ValueError(f"Ambiguous duplicate file: {path.name}")
        index[path.name] = path
    wanted = official_rows()
    missing = [name for row in wanted for name in (row["s2"], row["label"]) if name not in index]
    write_json(out / "missing_files.json", missing)
    if missing:
        raise FileNotFoundError(f"{len(missing)} required GeoTIFF files missing; see missing_files.json")
    samples, excluded = [], []
    for row in wanted:
        s2path, labpath = index[row["s2"]], index[row["label"]]
        with rasterio.open(s2path) as s2, rasterio.open(labpath) as lab:
            if s2.count != 13 or lab.count != 1:
                raise ValueError(f"{row['id']}: expected 13 S2 bands and one label band")
            if (s2.crs is None or s2.crs != lab.crs or s2.shape != lab.shape
                    or not s2.transform.almost_equals(lab.transform, precision=1e-10)):
                raise ValueError(f"{row['id']}: image / label geometry mismatch; do not silently resize")
            target = lab.read(1)
            values = set(np.unique(target).tolist())
            if not values <= {-1, 0, 1, 255}:
                raise ValueError(f"{row['id']}: unknown label values {values}")
            # The official hand-label convention is -1 invalid, 0 land, 1 water.
            valid = (target == 0) | (target == 1)
            if not valid.any():
                excluded.append({"id": row["id"], "split": row["split"], "reason": "all_labels_invalid"})
                continue
            rgb = s2.read([4, 3, 2]).astype(np.float32)
            if not np.isfinite(rgb).all():
                raise ValueError(f"{row['id']}: non-finite RGB values; fix source data explicitly")
            # Fixed radiometry, independent of label or split; no per-image histogram tuning.
            rgb = np.rint(np.clip(rgb / (10000.0 * reflectance_max), 0, 1) * 255).astype(np.uint8)
            areas = pixel_areas(lab.crs, lab.transform, lab.height, lab.width)
            image_rel, target_rel = f"rgb/{row['id']}.png", f"targets/{row['id']}.npz"
            (out / "rgb").mkdir(exist_ok=True)
            (out / "targets").mkdir(exist_ok=True)
            Image.fromarray(rgb.transpose(1, 2, 0)).save(out / image_rel)
            np.savez_compressed(out / target_rel, label=(target == 1).astype(np.uint8),
                                valid=valid.astype(np.uint8), area_m2=areas)
            samples.append({"id": row["id"], "split": row["split"], "image": image_rel,
                            "target": target_rel, "height": lab.height, "width": lab.width,
                            "crs": str(lab.crs), "transform": list(lab.transform)[:6],
                            "image_sha256": sha256(out / image_rel),
                            "target_sha256": sha256(out / target_rel),
                            "s2_sha256": sha256(s2path), "label_sha256": sha256(labpath),
                            "valid_pixels": int(valid.sum()),
                            "water_pixels": int(((target == 1) & valid).sum())})
    obj = {"schema": 1, "dataset": "Sen1Floods11-v1.1-handlabeled",
           "radiometry": {"bands_one_based": [4, 3, 2], "scale": 10000,
                          "clip_reflectance": [0, reflectance_max]},
           "expected_counts": {"train": 252, "val": 89, "test": 90, "bolivia": 15},
           "excluded": excluded, "samples": samples}
    write_json(out / "manifest.json", obj)
    print({s: sum(r["split"] == s for r in samples) for s in SPLIT_FILES}, "excluded:", len(excluded))
    return obj


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--reflectance-max", type=float, default=0.3)
    a = p.parse_args()
    if a.reflectance_max <= 0:
        p.error("reflectance-max must be positive")
    build_manifest(a.raw, a.out, a.reflectance_max)


if __name__ == "__main__":
    main()
