import numpy as np
from ..errors import require


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def calculate(mask, labels=None):
    require(mask.ndim == 2, 422, "MASK_GRID", "掩膜必须是二维网格")
    if labels is not None:
        require(
            labels.shape == mask.shape, 422, "LABEL_GRID", "参考标签与原图网格不一致"
        )
        require(
            set(np.unique(labels).tolist()) <= set(range(11)) | {255},
            422,
            "LABEL_VALUES",
            "参考标签不符合 FloodNet 类别定义",
        )
    valid = labels != 255 if labels is not None else np.ones_like(mask, dtype=bool)
    count = int(valid.sum())
    require(count > 0, 422, "EMPTY_VALID_REGION", "有效像素数为零，无法统计")
    pred = mask.astype(bool) & valid
    pixels = int(pred.sum())
    metrics = {
        "pred_pixels": pixels,
        "valid_pixels": count,
        "coverage_percent": 100 * pixels / count,
        "scene_threshold_percent": 1,
        "scene_screen_positive": pixels / count >= 0.01,
        "validity_source": "label_non_255" if labels is not None else "full_image",
        "coverage_definition": "影像有效区域内预测受淹道路像素比例",
        "area_m2": None,
    }
    evaluation = None
    if labels is not None:
        gt = (labels == 3) & valid
        tp, fp, fn = (int(a.sum()) for a in [pred & gt, pred & ~gt, ~pred & gt])
        evaluation = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "gt_pixels": int(gt.sum()),
            "iou": ratio(tp, tp + fp + fn),
            "precision": ratio(tp, tp + fp),
            "recall": ratio(tp, tp + fn),
            "gt_coverage_percent": 100 * int(gt.sum()) / count,
            "coverage_error_pp": 100 * abs(pixels - int(gt.sum())) / count,
            "null_reason": "分母为零的指标为 null；无目标影像不人为设置 IoU=1",
        }
    return metrics, evaluation


def summarize(rows):
    n = len(rows)
    tp, fp, fn = (sum(row[k] for row in rows) for k in ["tp", "fp", "fn"])
    positives = [r for r in rows if r["gt_pixels"] > 0]
    negatives = [r for r in rows if r["gt_pixels"] == 0]
    return {
        "n": n,
        "n_positive": len(positives),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "global_iou": ratio(tp, tp + fp + fn),
        "coverage_mae_pp": sum(
            100 * abs(r["pred_pixels"] - r["gt_pixels"]) / r["valid_pixels"]
            for r in rows
        )
        / n
        if n
        else None,
        "scene_tp": sum(
            r["pred_pixels"] / r["valid_pixels"] >= 0.01 for r in positives
        ),
        "scene_fn": sum(r["pred_pixels"] / r["valid_pixels"] < 0.01 for r in positives),
        "scene_fp": sum(
            r["pred_pixels"] / r["valid_pixels"] >= 0.01 for r in negatives
        ),
        "scene_tn": sum(r["pred_pixels"] / r["valid_pixels"] < 0.01 for r in negatives),
    }
