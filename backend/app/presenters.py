from sqlalchemy import select, func
from .models import ImageAsset, AnalysisTask, Prediction, Review, User
from .services.catalog import match_image


def fields(obj, keys):
    return {k: getattr(obj, k) for k in keys.split()}


def project_out(db, project, role):
    count = lambda model, *filters: db.scalar(
        select(func.count())
        .select_from(model)
        .where(model.project_id == project.id, *filters)
    )
    return {
        **fields(project, "id name description archived is_demo created_at"),
        "role": role,
        "image_count": count(ImageAsset),
        "queued_count": count(
            AnalysisTask,
            AnalysisTask.status.not_in(["SUCCEEDED", "FAILED", "CANCELED"]),
        ),
        "pending_review_count": count(Prediction, Prediction.review_revision == 0),
    }


def image_out(image):
    known = match_image(image)
    return {
        **fields(
            image,
            "id project_id name sample_id split input_sha256 width height display_asset_id thumbnail_asset_id label_asset_id coordinate_mode acquired_at created_at",
        ),
        "available_strategies": list(known["masks"]) if known else [],
        'location': image.transforms.get('location') or (known.get('location') if known else None),
        'native_size': image.transforms.get('native_size') or (known.get('native_size') if known else None),
        'acquired_at': image.acquired_at or (known.get('acquired_at') if known else None),
    }


def task_out(db, task):
    prediction = db.scalar(select(Prediction.id).where(Prediction.task_id == task.id))
    return {
        **fields(
            task,
            "id project_id image_id status config logs error attempt parent_id created_at finished_at",
        ),
        "prediction_id": prediction,
    }


def review_out(db, review):
    return {
        **fields(review, "id revision decision note annotations created_at"),
        "author": db.get(User, review.created_by).username,
    }


def prediction_out(db, prediction):
    return {
        **fields(
            prediction,
            "id task_id image_id project_id contract metrics evaluation mask_asset_id overlay_asset_id layer_asset_id difference_asset_id gt_layer_asset_id review_revision created_at",
        ),
        "reviews": [
            review_out(db, r)
            for r in db.scalars(
                select(Review)
                .where(Review.prediction_id == prediction.id)
                .order_by(Review.revision.desc())
            )
        ],
    }


def report_out(report):
    return fields(
        report, "id prediction_id project_id status snapshot files error created_at"
    )
