import time
from typing import Annotated

from fastapi import APIRouter, Form, Header, Query, Request, UploadFile
from pydantic import ValidationError
from sqlalchemy import select, update

from ..config import settings
from ..errors import DomainError, require
from ..models import AnalysisTask, ImageAsset
from ..presenters import task_out
from ..schemas import ImportMetadata, TaskIn, TaskOut
from ..security import DB, Actor, audit, project_access
from ..services.catalog import PREPROCESS, historical_mask
from ..services.inference import health
from ..services.storage import read_mask, save_asset, sha256
from ..services.tasks import TERMINAL, config_digest

router = APIRouter(tags=["tasks"])
IdempotencyKey = Annotated[
    str, Header(alias="Idempotency-Key", min_length=8, max_length=120)
]


def get_image(db, user, image_id):
    image = db.get(ImageAsset, image_id)
    require(image, 404, "NOT_FOUND", "影像不存在")
    project_access(db, user, image.project_id, {"analyst"}, True)
    return image


def create(db, user, image, config, key, request, fingerprint=None, parent=None):
    digest = config_digest({"image_id": image.id, **(fingerprint or config)})
    existing = db.scalar(
        select(AnalysisTask).where(
            AnalysisTask.project_id == image.project_id,
            AnalysisTask.idempotency_key == key,
        )
    )
    if existing:
        require(
            existing.request_digest == digest,
            409,
            "IDEMPOTENCY_CONFLICT",
            "该幂等键已用于不同请求",
        )
        return existing
    task = AnalysisTask(
        project_id=image.project_id,
        image_id=image.id,
        created_by=user.id,
        config=config,
        idempotency_key=key,
        request_digest=digest,
        parent_id=parent.id if parent else None,
        attempt=parent.attempt + 1 if parent else 1,
        logs=[{"stage": "QUEUED", "message": "任务已入队", "at": time.time()}],
    )
    db.add(task)
    db.flush()
    audit(
        db,
        user,
        "task.create",
        task.id,
        image.project_id,
        details={"mode": config["mode"]},
        request=request,
    )
    db.commit()
    return task


@router.post("/analysis-tasks", response_model=TaskOut, status_code=202)
def submit(body: TaskIn, key: IdempotencyKey, user: Actor, db: DB, request: Request):
    image = get_image(db, user, body.image_id)
    config = {
        **body.model_dump(exclude={"image_id"}),
        "threshold": 0,
        "preprocess_version": PREPROCESS,
    }
    if db.scalar(
        select(AnalysisTask.id).where(
            AnalysisTask.project_id == image.project_id,
            AnalysisTask.idempotency_key == key,
        )
    ):
        return task_out(db, create(db, user, image, config, key, request))
    if body.mode == "historical_replay":
        historical_mask(image, config)
    else:
        state = health()
        require(state["available"], 503, "MODEL_UNAVAILABLE", state["reason"])
    return task_out(db, create(db, user, image, config, key, request))


@router.post(
    "/images/{image_id}/import-result", response_model=TaskOut, status_code=202
)
async def import_result(
    image_id: str,
    mask: UploadFile,
    metadata: Annotated[str, Form()],
    key: IdempotencyKey,
    user: Actor,
    db: DB,
    request: Request,
):
    image = get_image(db, user, image_id)
    try:
        meta = ImportMetadata.model_validate_json(metadata)
    except ValidationError:
        raise DomainError(422, "IMPORT_METADATA", "元数据清单不符合导入协议")
    require(
        meta.input_sha256 == image.input_sha256
        and (meta.width, meta.height) == (image.width, image.height),
        422,
        "IMPORT_PAIR",
        "元数据与当前影像不匹配",
    )
    require(
        mask.content_type == "image/png"
        and (mask.filename or "").lower().endswith(".png"),
        422,
        "MASK_FORMAT",
        "掩膜应为 PNG 文件",
    )
    data = await mask.read(settings.max_upload_bytes + 1)
    require(
        sha256(data) == meta.mask_sha256, 422, "MASK_CHECKSUM", "掩膜哈希与清单不一致"
    )
    read_mask(data, image.width, image.height)
    fingerprint = {"mode": "manual_import", **meta.model_dump()}
    digest = config_digest({"image_id": image.id, **fingerprint})
    existing = db.scalar(
        select(AnalysisTask).where(
            AnalysisTask.project_id == image.project_id,
            AnalysisTask.idempotency_key == key,
        )
    )
    if existing:
        require(
            existing.request_digest == digest, 409, "IDEMPOTENCY_CONFLICT", "幂等键冲突"
        )
        return task_out(db, existing)
    asset = save_asset(db, image.project_id, data, "external-mask.png", "image/png")
    return task_out(
        db,
        create(
            db,
            user,
            image,
            {**fingerprint, "mask_asset_id": asset.id},
            key,
            request,
            fingerprint=fingerprint,
        ),
    )


@router.get("/analysis-tasks", response_model=list[TaskOut])
def tasks(
    project_id: str,
    user: Actor,
    db: DB,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    project_access(db, user, project_id)
    return [
        task_out(db, t)
        for t in db.scalars(
            select(AnalysisTask)
            .where(AnalysisTask.project_id == project_id)
            .order_by(AnalysisTask.created_at.desc(), AnalysisTask.id)
            .offset(offset)
            .limit(limit)
        )
    ]


@router.get("/analysis-tasks/{task_id}", response_model=TaskOut)
def task_detail(task_id: str, user: Actor, db: DB):
    task = db.get(AnalysisTask, task_id)
    require(task, 404, "NOT_FOUND", "任务不存在")
    project_access(db, user, task.project_id)
    return task_out(db, task)


@router.post("/analysis-tasks/{task_id}/cancel", response_model=TaskOut)
def cancel(task_id: str, user: Actor, db: DB, request: Request):
    task = db.get(AnalysisTask, task_id)
    require(task, 404, "NOT_FOUND", "任务不存在")
    project_access(db, user, task.project_id, {"analyst"}, True)
    require(task.status not in TERMINAL, 409, "TASK_TERMINAL", "已结束任务不能取消")
    status = "CANCELED" if task.status == "QUEUED" else "CANCEL_REQUESTED"
    result = db.execute(
        update(AnalysisTask)
        .where(AnalysisTask.id == task.id, AnalysisTask.status == task.status)
        .values(
            status=status,
            finished_at=time.time() if status == "CANCELED" else None,
            logs=task.logs
            + [{"stage": status, "message": "用户请求取消", "at": time.time()}],
        )
    )
    require(result.rowcount, 409, "TASK_CHANGED", "任务状态已变化，请刷新")
    audit(db, user, "task.cancel", task.id, task.project_id, request=request)
    db.commit()
    db.refresh(task)
    return task_out(db, task)


@router.post("/analysis-tasks/{task_id}/retry", response_model=TaskOut, status_code=202)
def retry(task_id: str, key: IdempotencyKey, user: Actor, db: DB, request: Request):
    task = db.get(AnalysisTask, task_id)
    require(task, 404, "NOT_FOUND", "任务不存在")
    image = get_image(db, user, task.image_id)
    require(
        task.status in {"FAILED", "CANCELED"} and task.attempt < 3,
        409,
        "RETRY_NOT_ALLOWED",
        "仅可重试失败或取消任务，最多三次执行",
    )
    return task_out(db, create(db, user, image, task.config, key, request, parent=task))
