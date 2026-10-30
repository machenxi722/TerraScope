import csv
import io
from typing import Literal

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response
from sqlalchemy import select, text

from .. import __version__
from ..config import settings
from ..errors import require
from ..models import ImageAsset, ModelVersion, Prediction
from ..presenters import fields, project_out
from ..schemas import ProjectOut
from ..security import DB, Actor, audit, project_access
from ..services.catalog import catalog, checked_json
from ..services.inference import health
from ..services.metrics import summarize
from ..services.seed import seed_demo

router = APIRouter(tags=["system"])


@router.get("/health")
def health_check(db: DB):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "version": __version__}


@router.get("/system/capabilities")
def capabilities(user: Actor):
    return {
        "version": __version__,
        "data_version": "20261018-full" if settings.library_dir.joinpath('manifest.json').exists() else "20261016",
        "coordinate_mode": "pixel",
        "historical_replay": {
            "available": bool(catalog()),
            "reason": "真实案例按输入哈希和模型配置匹配",
        },
        "manual_import": {
            "available": True,
            "reason": "导入二值 PNG 与严格匹配的元数据清单",
        },
        "live_inference": health(),
        "geographic": {"available": any(r.get('location') for r in catalog()),
                       "reason": 'WGS84 拍摄点定位；解译采用原始像素网格',
                       'gps_count': sum(bool(r.get('location')) for r in catalog()), 'scene_count':len(catalog())},
        "deployment": {
            "database": "PostgreSQL"
            if settings.database_url.startswith("postgresql")
            else "SQLite（本地开发）",
            "worker": settings.worker_mode,
        },
        "max_upload_bytes": settings.max_upload_bytes,
        "max_pixels": settings.max_pixels,
    }


@router.get("/system/models")
def models(user: Actor, db: DB):
    return [
        fields(m, "id name delta_sha256 base_sha256 preprocess_version strategies")
        for m in db.scalars(select(ModelVersion))
    ]


@router.post("/system/demo", response_model=ProjectOut, status_code=201)
def initialize_demo(user: Actor, db: DB, request: Request):
    require(user.is_admin, 403, "ROLE_FORBIDDEN", "仅系统管理员可初始化示范项目")
    project = seed_demo(db, user)
    audit(db, user, "demo.initialize", project.id, project.id, request=request)
    db.commit()
    return project_out(db, project, "admin")


@router.get("/experiments/floodnet/metrics")
def experiment(
    user: Actor,
    db: DB,
    project_id: str,
    split: Literal["test", "holdout", "val"] = "test",
    strategy: Literal["single_view", "tta4"] = "tta4",
    q: str = "",
    offset: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=200),
):
    project_access(db, user, project_id)
    path = settings.demo_dir / "experiments" / f"{strategy}_{split}.json"
    require(path.exists(), 404, "EXPERIMENT_MISSING", "实验统计资料缺失")
    data = checked_json(f"experiments/{strategy}_{split}.json")
    rows = data["per_image"]
    images = {
        i.sample_id: i.id
        for i in db.scalars(
            select(ImageAsset).where(
                ImageAsset.project_id == project_id, ImageAsset.split == split
            )
        )
    }
    available_cases = {
        r["sample_id"]
        for r in catalog()
        if r["split"] == split and strategy in r["masks"]
    }
    matched_predictions = {}
    for pred in db.scalars(
        select(Prediction)
        .where(
            Prediction.project_id == project_id,
            Prediction.image_id.in_(list(images.values())),
        )
        .order_by(Prediction.created_at.desc(), Prediction.id)
    ):
        if (
            pred.contract.get("source_mode") == "historical_replay"
            and pred.contract.get("strategy") == strategy
        ):
            matched_predictions.setdefault(pred.image_id, pred.id)
    selected = sorted([r for r in rows if q.strip() in r["id"]], key=lambda r: r["id"])
    records = [
        {
            **r,
            "coverage_percent": 100 * r["pred_pixels"] / r["valid_pixels"],
            "image_id": images.get(r["id"]),
            "prediction_id": matched_predictions.get(images.get(r["id"])),
            "case_available": r["id"] in available_cases,
            "availability": "image_and_statistics"
            if r["id"] in images
            else "statistics_only",
        }
        for r in selected[offset : offset + limit]
    ]
    comparison = []
    for name in ["single_view", "tta4"]:
        subset = checked_json(f"experiments/{name}_{split}.json")["per_image"]
        comparison.append({"strategy": name, **summarize(subset)})
    baselines = checked_json("experiments/baselines.json")
    return {
        "dataset": "FloodNet",
        "split": split,
        "strategy": strategy,
        "summary": summarize(rows),
        "comparison": comparison,
        "records": records,
        "total": len(selected),
        "offset": offset,
        "limit": limit,
        "baselines": baselines,
        "boundary": "测试集与留出集来自同一灾害事件，分区分别评价。",
    }


@router.get("/experiments/floodnet/export")
def export_experiment(
    user: Actor,
    db: DB,
    project_id: str,
    split: Literal["test", "holdout", "val"] = "test",
    strategy: Literal["single_view", "tta4"] = "tta4",
    q: str = "",
):
    project_access(db, user, project_id)
    data = checked_json(f"experiments/{strategy}_{split}.json")
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "sample_id",
            "split",
            "strategy",
            "valid_pixels",
            "pred_pixels",
            "gt_pixels",
            "tp",
            "fp",
            "fn",
            "iou",
            "coverage_percent",
        ]
    )
    for row in sorted(data["per_image"], key=lambda r: r["id"]):
        if q.strip() not in row["id"]:
            continue
        writer.writerow(
            [
                row["id"],
                split,
                strategy,
                *[
                    row[k]
                    for k in [
                        "valid_pixels",
                        "pred_pixels",
                        "gt_pixels",
                        "tp",
                        "fp",
                        "fn",
                        "iou",
                    ]
                ],
                100 * row["pred_pixels"] / row["valid_pixels"],
            ]
        )
    return Response(
        output.getvalue().encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="floodnet-{split}-{strategy}.csv"'
        },
    )
