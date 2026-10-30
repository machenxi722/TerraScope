import io
import math
from datetime import UTC, datetime
from itertools import pairwise

from fastapi import APIRouter, Query, Request
from fastapi.responses import FileResponse
from PIL import Image
from sqlalchemy import select, update

from ..errors import require
from ..models import AssetFile, ImageAsset, Prediction, ReportSnapshot, Review
from ..presenters import image_out, prediction_out, report_out, review_out
from ..schemas import PredictionOut, ReportIn, ReportOut, ReviewIn, ReviewOut
from ..security import DB, Actor, audit, project_access
from ..services.storage import asset_path, read_asset
from ..services.tasks import config_digest
from .tasks import IdempotencyKey

router = APIRouter(tags=["results"])


def get_prediction(db, user, prediction_id, roles=None, writable=False):
    pred = db.get(Prediction, prediction_id)
    require(pred, 404, "NOT_FOUND", "预测结果不存在")
    project_access(db, user, pred.project_id, roles, writable)
    return pred


@router.get("/predictions", response_model=list[PredictionOut])
def predictions(
    image_id: str,
    user: Actor,
    db: DB,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    image = db.get(ImageAsset, image_id)
    require(image, 404, "NOT_FOUND", "影像不存在")
    project_access(db, user, image.project_id)
    return [
        prediction_out(db, p)
        for p in db.scalars(
            select(Prediction)
            .where(Prediction.image_id == image_id)
            .order_by(Prediction.created_at.desc(), Prediction.id)
            .offset(offset)
            .limit(limit)
        )
    ]


@router.get("/predictions/{prediction_id}", response_model=PredictionOut)
def prediction(prediction_id: str, user: Actor, db: DB):
    return prediction_out(db, get_prediction(db, user, prediction_id))


@router.get("/predictions/{prediction_id}/pixel")
def pixel(
    prediction_id: str, user: Actor, db: DB, x: int = Query(ge=0), y: int = Query(ge=0)
):
    pred = get_prediction(db, user, prediction_id)
    image = db.get(ImageAsset, pred.image_id)
    require(
        x < image.width and y < image.height,
        422,
        "PIXEL_BOUNDS",
        "像素坐标超出影像范围",
    )
    rgb = Image.open(io.BytesIO(read_asset(db, image.display_asset_id))).getpixel(
        (x, y)
    )
    mask = Image.open(io.BytesIO(read_asset(db, pred.mask_asset_id))).getpixel((x, y))
    label = (
        Image.open(io.BytesIO(read_asset(db, image.label_asset_id))).getpixel((x, y))
        if image.label_asset_id
        else None
    )
    return {
        "x": x,
        "y": y,
        "center": [x + 0.5, y + 0.5],
        "rgb": rgb,
        "predicted": bool(mask),
        "label": label,
        "valid": label != 255 if label is not None else True,
    }


@router.post(
    "/predictions/{prediction_id}/reviews", response_model=ReviewOut, status_code=201
)
def save_review(
    prediction_id: str, body: ReviewIn, user: Actor, db: DB, request: Request
):
    pred = get_prediction(db, user, prediction_id, {"reviewer"}, True)
    image = db.get(ImageAsset, pred.image_id)
    for polygon in body.annotations:
        points = polygon.coordinates
        require(points[0] == points[-1], 422, "POLYGON_OPEN", "复核多边形必须闭合")
        require(
            all(
                math.isfinite(x)
                and math.isfinite(y)
                and 0 <= x <= image.width
                and 0 <= y <= image.height
                for x, y in points
            ),
            422,
            "POLYGON_BOUNDS",
            "复核区域必须在原图范围内",
        )
        area = abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in pairwise(points))) / 2
        require(area > 0, 422, "POLYGON_EMPTY", "复核区域面积必须大于零")
    updated = db.execute(
        update(Prediction)
        .where(
            Prediction.id == pred.id, Prediction.review_revision == body.base_revision
        )
        .values(review_revision=body.base_revision + 1)
    )
    require(
        updated.rowcount,
        409,
        "REVIEW_CONFLICT",
        "已有新的复核版本，请刷新并比较后重新提交",
    )
    review = Review(
        prediction_id=pred.id,
        revision=body.base_revision + 1,
        created_by=user.id,
        decision=body.decision,
        note=body.note,
        annotations=[a.model_dump() for a in body.annotations],
    )
    db.add(review)
    db.flush()
    audit(
        db,
        user,
        "review.create",
        review.id,
        pred.project_id,
        details={"revision": review.revision, "prediction_id": pred.id},
        request=request,
    )
    db.commit()
    return review_out(db, review)


@router.post("/reports", response_model=ReportOut, status_code=202)
def create_report(
    body: ReportIn, key: IdempotencyKey, user: Actor, db: DB, request: Request
):
    pred = get_prediction(db, user, body.prediction_id, {"analyst", "reviewer"}, True)
    digest = config_digest(body.model_dump())
    existing = db.scalar(
        select(ReportSnapshot).where(
            ReportSnapshot.project_id == pred.project_id,
            ReportSnapshot.idempotency_key == key,
        )
    )
    if existing:
        require(
            existing.request_digest == digest,
            409,
            "IDEMPOTENCY_CONFLICT",
            "该幂等键已用于其他快照",
        )
        return report_out(existing)
    require(
        body.review_revision <= pred.review_revision,
        409,
        "REVIEW_CONFLICT",
        "指定复核版本不存在",
    )
    review = (
        db.scalar(
            select(Review).where(
                Review.prediction_id == pred.id, Review.revision == body.review_revision
            )
        )
        if body.review_revision
        else None
    )
    require(
        body.review_revision == 0 or review,
        409,
        "REVIEW_CONFLICT",
        "指定复核版本不存在",
    )
    project, _ = project_access(db, user, pred.project_id)
    image = db.get(ImageAsset, pred.image_id)
    result = prediction_out(db, pred)
    result["review_revision"] = body.review_revision
    result["reviews"] = [review_out(db, review)] if review else []
    snapshot = {
        "project": {
            "id": project.id,
            "name": project.name,
            "description": project.description,
        },
        "image": image_out(image),
        "prediction": result,
        "review": review_out(db, review) if review else None,
        "review_revision": body.review_revision,
        "template_version": "1.1.0",
        "snapshot_at": datetime.now(UTC).isoformat(),
    }
    report = ReportSnapshot(
        project_id=pred.project_id,
        prediction_id=pred.id,
        created_by=user.id,
        snapshot=snapshot,
        idempotency_key=key,
        request_digest=digest,
    )
    db.add(report)
    db.flush()
    audit(
        db,
        user,
        "report.create",
        report.id,
        pred.project_id,
        details={"review_revision": body.review_revision},
        request=request,
    )
    db.commit()
    return report_out(report)


@router.get("/reports", response_model=list[ReportOut])
def reports(
    project_id: str,
    user: Actor,
    db: DB,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    project_access(db, user, project_id)
    return [
        report_out(r)
        for r in db.scalars(
            select(ReportSnapshot)
            .where(ReportSnapshot.project_id == project_id)
            .order_by(ReportSnapshot.created_at.desc(), ReportSnapshot.id)
            .offset(offset)
            .limit(limit)
        )
    ]


@router.get("/reports/{report_id}", response_model=ReportOut)
def report_detail(report_id: str, user: Actor, db: DB):
    report = db.get(ReportSnapshot, report_id)
    require(report, 404, "NOT_FOUND", "报告不存在")
    project_access(db, user, report.project_id)
    return report_out(report)


@router.post("/reports/{report_id}/retry", response_model=ReportOut)
def retry_report(report_id: str, user: Actor, db: DB, request: Request):
    report = db.get(ReportSnapshot, report_id)
    require(report, 404, "NOT_FOUND", "报告不存在")
    project_access(db, user, report.project_id, {"analyst", "reviewer"}, True)
    require(report.status == "FAILED", 409, "RETRY_NOT_ALLOWED", "仅可重试失败报告")
    report.status, report.error, report.lease_until = "QUEUED", None, 0
    audit(db, user, "report.retry", report.id, report.project_id, request=request)
    db.commit()
    return report_out(report)


@router.get("/assets/{asset_id}/download")
def download(asset_id: str, user: Actor, db: DB, inline: bool = False):
    asset = db.get(AssetFile, asset_id)
    require(asset, 404, "NOT_FOUND", "资产不存在")
    project_access(db, user, asset.project_id)
    read_asset(db, asset_id)
    return FileResponse(
        asset_path(asset),
        media_type=asset.media_type,
        filename=asset.filename,
        content_disposition_type="inline" if inline else "attachment",
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "ETag": '"' + asset.sha256 + '"',
        },
    )
