import io
import json
import logging
import time
from datetime import UTC, datetime

import numpy as np
from PIL import Image
from sqlalchemy import select, update

from ..db import SessionLocal
from ..errors import DomainError, require
from ..models import AnalysisTask, ImageAsset, Prediction, uid
from .catalog import DELTA_SHA, PREPROCESS, historical_mask
from .inference import infer
from .metrics import calculate
from .storage import png, read_asset, read_mask, save_asset, sha256

TERMINAL = {"SUCCEEDED", "FAILED", "CANCELED"}
log = logging.getLogger(__name__)


def config_digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


class Canceled(Exception):
    def __init__(self, cancel_remote=False):
        self.cancel_remote = cancel_remote


def claim(task_id):
    token = uid()
    with SessionLocal() as db:
        result = db.execute(
            update(AnalysisTask)
            .where(
                AnalysisTask.id == task_id,
                AnalysisTask.status.not_in(TERMINAL),
                AnalysisTask.lease_until < time.time(),
            )
            .values(lease_token=token, lease_until=time.time() + 120)
        )
        db.commit()
        return token if result.rowcount else None


def checkpoint(task_id, token, stage, message):
    with SessionLocal() as db:
        task = db.get(AnalysisTask, task_id)
        if task.lease_token != token:
            raise Canceled()
        if task.status == "CANCEL_REQUESTED":
            task.status = "CANCELED"
            task.finished_at = time.time()
            task.lease_until = 0
            task.logs = task.logs + [
                {
                    "stage": "CANCELED",
                    "message": "已在安全检查点取消",
                    "at": time.time(),
                }
            ]
            db.commit()
            raise Canceled(cancel_remote=True)
        require(task.status not in TERMINAL, 409, "TASK_TERMINAL", "任务已结束")
        # CAS prevents a simultaneous cancellation from being overwritten.
        logs = (
            task.logs
            if task.logs
            and task.logs[-1]["stage"] == stage
            and task.logs[-1]["message"] == message
            else task.logs + [{"stage": stage, "message": message, "at": time.time()}]
        )
        result = db.execute(
            update(AnalysisTask)
            .where(
                AnalysisTask.id == task_id,
                AnalysisTask.lease_token == token,
                AnalysisTask.status == task.status,
            )
            .values(status=stage, logs=logs, lease_until=time.time() + 120)
        )
        db.commit()
        if not result.rowcount:
            return checkpoint(task_id, token, stage, message)


def color_layer(mask, color):
    layer = np.zeros((*mask.shape, 4), dtype=np.uint8)
    layer[mask] = color
    return Image.fromarray(layer)


def run_task(task_id):
    token = claim(task_id)
    if not token:
        return
    try:
        checkpoint(task_id, token, "VALIDATING", "核验输入文件摘要与网格")
        with SessionLocal() as db:
            task = db.get(AnalysisTask, task_id)
            image = db.get(ImageAsset, task.image_id)
            original = read_asset(db, image.original_asset_id)
            require(
                sha256(original) == image.input_sha256,
                422,
                "INPUT_CHECKSUM",
                "输入影像摘要变化",
            )
            rgb_bytes = read_asset(db, image.display_asset_id)
            rgb = Image.open(io.BytesIO(rgb_bytes)).convert("RGB")
            labels = (
                np.asarray(
                    Image.open(io.BytesIO(read_asset(db, image.label_asset_id)))
                ).copy()
                if image.label_asset_id
                else None
            )
            config = task.config
            runtime = {}
            if config["mode"] == "historical_replay":
                checkpoint(
                    task_id,
                    token,
                    "LOADING_ARTIFACT",
                    "严格匹配哈希、分区、模型和策略，加载历史掩膜",
                )
                mask_bytes = historical_mask(image, config)
            elif config["mode"] == "manual_import":
                checkpoint(task_id, token, "LOADING_ARTIFACT", "读取已校验的外部掩膜")
                mask_bytes = read_asset(db, config["mask_asset_id"])
            else:
                mask_bytes, runtime = infer(
                    task, image, original, lambda s, m: checkpoint(task_id, token, s, m)
                )
            checkpoint(
                task_id, token, "POSTPROCESSING", "按原始网格核算像素，生成叠加图和证据"
            )
            mask = read_mask(mask_bytes, image.width, image.height)
            metrics, evaluation = calculate(mask, labels)
            canonical = png(Image.fromarray(mask.astype(np.uint8) * 255))
            layer = color_layer(mask, [230, 93, 62, 190])
            overlay = Image.alpha_composite(rgb.convert("RGBA"), layer).convert("RGB")
            files = {}
            for name, content in [
                ("mask", canonical),
                ("layer", png(layer)),
                ("overlay", png(overlay)),
            ]:
                files[name] = save_asset(
                    db, image.project_id, content, name + ".png", "image/png"
                )
            if labels is not None:
                gt, valid = labels == 3, labels != 255
                diff = np.zeros((*mask.shape, 4), dtype=np.uint8)
                diff[mask & gt & valid] = [60, 160, 105, 220]
                diff[mask & ~gt & valid] = [220, 80, 70, 220]
                diff[~mask & gt & valid] = [235, 185, 60, 230]
                files["difference"] = save_asset(
                    db,
                    image.project_id,
                    png(Image.fromarray(diff)),
                    "difference.png",
                    "image/png",
                )
                files["gt_layer"] = save_asset(
                    db,
                    image.project_id,
                    png(color_layer(gt & valid, [60, 140, 220, 190])),
                    "reference.png",
                    "image/png",
                )
            pred_id = uid()
            contract = {
                "prediction_id": pred_id,
                "image_id": image.id,
                "source_mode": config["mode"],
                "model_version": config["model_version"],
                "strategy": config["strategy"],
                "threshold": config.get("threshold", 0),
                "preprocess_version": config.get("preprocess_version", PREPROCESS),
                "width": image.width,
                "height": image.height,
                "coordinate_mode": "pixel",
                "pixel_origin": "top_left",
                "pixel_center": [0.5, 0.5],
                "mask_asset_id": files["mask"].id,
                "input_sha256": image.input_sha256,
                "mask_sha256": files["mask"].sha256,
                "source_mask_sha256": sha256(mask_bytes),
                "validity_source": metrics["validity_source"],
                "created_at": datetime.now(UTC).isoformat(),
                "split": image.split,
                "sample_id": image.sample_id,
                "model_verified": config["mode"] != "manual_import",
                "delta_sha256": DELTA_SHA
                if config["mode"] != "manual_import"
                else None,
                "runtime": runtime,
                "external_source": config.get("source"),
                "cache_reused": False,
            }
            # Only the current lease owner can publish. Cancel and result publication serialize on this row.
            result = db.execute(
                update(AnalysisTask)
                .where(
                    AnalysisTask.id == task_id,
                    AnalysisTask.lease_token == token,
                    AnalysisTask.status == "POSTPROCESSING",
                )
                .values(status="SUCCEEDED", finished_at=time.time(), lease_until=0)
            )
            if not result.rowcount:
                db.rollback()
                checkpoint(task_id, token, "POSTPROCESSING", "发布前检查取消状态")
                return
            prediction = Prediction(
                id=pred_id,
                task_id=task_id,
                project_id=image.project_id,
                image_id=image.id,
                contract=contract,
                metrics=metrics,
                evaluation=evaluation,
                mask_asset_id=files["mask"].id,
                overlay_asset_id=files["overlay"].id,
                layer_asset_id=files["layer"].id,
                difference_asset_id=files["difference"].id
                if "difference" in files
                else None,
                gt_layer_asset_id=files["gt_layer"].id if "gt_layer" in files else None,
            )
            db.add(prediction)
            db.expire(task)
            task.logs = task.logs + [
                {
                    "stage": "SUCCEEDED",
                    "message": "结果与资产已原子提交",
                    "at": time.time(),
                }
            ]
            db.commit()
    except Canceled:
        return
    except Exception as exc:
        log.exception("Analysis execution failed: %s", task_id)
        with SessionLocal() as db:
            task = db.get(AnalysisTask, task_id)
            if task and task.lease_token == token and task.status not in TERMINAL:
                task.status = (
                    "CANCELED" if task.status == "CANCEL_REQUESTED" else "FAILED"
                )
                task.error = (
                    {"code": exc.code, "message": exc.message}
                    if isinstance(exc, DomainError)
                    else {
                        "code": "PROCESSING_FAILED",
                        "message": "处理失败，请根据任务 ID 检查服务日志",
                    }
                )
                task.finished_at = time.time()
                task.lease_until = 0
                task.logs = task.logs + [
                    {
                        "stage": task.status,
                        "message": task.error["message"],
                        "at": time.time(),
                    }
                ]
                db.commit()


def pending_ids():
    with SessionLocal() as db:
        return list(
            db.scalars(
                select(AnalysisTask.id)
                .where(
                    AnalysisTask.status.not_in(TERMINAL),
                    AnalysisTask.lease_until < time.time(),
                )
                .order_by(AnalysisTask.created_at)
                .limit(20)
            )
        )
