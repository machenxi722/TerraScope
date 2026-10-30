"""Fixed 0.5 threshold, all valid pixels, native georeferenced grid; no test-time tuning."""
import argparse
import csv
import time
from pathlib import Path

import numpy as np
import torch

from .cache import amp
from .common import check_deadline, deadline, load_tensor_file, write_json
from .dataset import CachedDataset, to_device
from .head import WaterHead, selected_logits


def sample_metrics(pred, label, valid, area):
    pred, label, valid = (np.asarray(a, dtype=bool) for a in (pred, label, valid))
    area = np.asarray(area, dtype=np.float64)
    tp = int((pred & label & valid).sum())
    fp = int((pred & ~label & valid).sum())
    fn = int((~pred & label & valid).sum())
    total_area = float(area[valid].sum())
    if total_area <= 0:
        raise ValueError("No valid area")
    pa, ga = float(area[pred & valid].sum()), float(area[label & valid].sum())
    return {"tp": tp, "fp": fp, "fn": fn, "valid_pixels": int(valid.sum()),
            "gt_water_pixels": int((label & valid).sum()),
            "iou": tp / (tp + fp + fn) if tp + fp + fn else None,
            "dice": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
            "valid_fraction": float(valid.mean()), "valid_area_m2": total_area,
            "pred_water_m2": pa, "gt_water_m2": ga,
            "area_abs_error_m2": abs(pa - ga), "area_error_pp": 100 * (pa - ga) / total_area,
            "area_abs_error_pp": 100 * abs(pa - ga) / total_area}


def aggregate(rows):
    if not rows:
        raise ValueError("No evaluated samples")
    tp, fp, fn = [sum(r[k] for r in rows) for k in ("tp", "fp", "fn")]
    ious = [r["iou"] for r in rows if r["iou"] is not None]
    positive = [r["iou"] for r in rows if r["gt_water_pixels"] > 0]
    negative = [r for r in rows if r["gt_water_pixels"] == 0]
    return {"n": len(rows), "micro_iou": tp / (tp + fp + fn) if tp + fp + fn else None,
            "micro_dice": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
            "macro_iou_nonempty_union": float(np.mean(ious)) if ious else None,
            "macro_iou_gt_positive": float(np.mean(positive)) if positive else None,
            "n_empty_gt": len(negative), "n_empty_both": sum(r["iou"] is None for r in rows),
            "empty_gt_mean_false_positive_pp": float(np.mean([r["area_abs_error_pp"] for r in negative])) if negative else None,
            "area_mae_pp": float(np.mean([r["area_abs_error_pp"] for r in rows])),
            "area_bias_pp": float(np.mean([r["area_error_pp"] for r in rows])),
            "area_mae_m2": float(np.mean([r["area_abs_error_m2"] for r in rows])),
            "confusion": {"tp": tp, "fp": fp, "fn": fn},
            "empty_union_policy": "IoU/Dice undefined; excluded from macro, counted separately",
            "threshold": 0.5}


def export_mask(path, pred, valid, row):
    import rasterio
    from affine import Affine
    data = np.where(valid, pred.astype(np.uint8), 255).astype(np.uint8)
    with rasterio.open(path, "w", driver="GTiff", height=data.shape[0], width=data.shape[1],
                       count=1, dtype="uint8", crs=row["crs"], transform=Affine(*row["transform"]),
                       nodata=255, compress="deflate") as dst:
        dst.write(data, 1)


@torch.no_grad()
def evaluate(model, dataset, device, end=float("inf"), export_dir=None):
    model.eval()
    rows = []
    if export_dir:
        Path(export_dir).mkdir(parents=True, exist_ok=True)
    for i in range(len(dataset)):
        check_deadline(end, reserve=5)
        feature, target, row = dataset[i]
        feature, gpu_target = to_device(feature, target, device)
        with amp(device):
            masks, ious = model(feature["raw_fpn"], feature["seg_hidden"])
            logits = selected_logits(masks, ious, target["label"].shape[-2:])
        pred = (logits[0, 0] > 0).cpu().numpy()
        label, valid, area = [target[k][0, 0].numpy() for k in ("label", "valid", "area_m2")]
        result = sample_metrics(pred, label, valid, area)
        rows.append({"id": row["id"], "split": row["split"], **result})
        if export_dir:
            export_mask(Path(export_dir) / f"{row['id']}.tif", pred, valid.astype(bool), row)
    return aggregate(rows), rows


def load_evaluation_head(cache, checkpoint, device):
    head, meta = WaterHead.load_base(Path(cache) / "base_head.pt")
    step = 0
    if checkpoint:
        ckpt = load_tensor_file(checkpoint)
        if ckpt["fingerprint"] != meta["fingerprint"]:
            raise ValueError("Adapter belongs to another model/prompt/data cache")
        head.load_state_dict(ckpt["state"], strict=True)
        step = ckpt["step"]
    return head.to(device), meta, step


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", required=True)
    p.add_argument("--cache", required=True)
    p.add_argument("--checkpoint", help="Omit for frozen fixed-prompt baseline R1")
    p.add_argument("--split", choices=["val", "test", "bolivia"], required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--device", default="cuda")
    p.add_argument("--hours", type=float, default=2)
    p.add_argument("--export-masks", action="store_true")
    a = p.parse_args()
    end = deadline(a.hours)
    out = Path(a.out)
    if out.exists() and any(out.iterdir()):
        raise FileExistsError("Use a new output directory to preserve previous results")
    out.mkdir(parents=True, exist_ok=True)
    dataset = CachedDataset(a.manifest, a.cache, a.split)
    head, meta, step = load_evaluation_head(a.cache, a.checkpoint, a.device)
    summary, rows = evaluate(head, dataset, a.device, end, out / "masks" if a.export_masks else None)
    summary.update({"split": a.split, "checkpoint": a.checkpoint, "step": step,
                    "fingerprint": meta["fingerprint"], "protocol": meta["protocol"]})
    write_json(out / "summary.json", summary)
    with open(out / "per_image.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(summary)


if __name__ == "__main__":
    main()
