import io
from sqlalchemy import select
from PIL import Image
from ..models import ImageAsset
from .storage import decode_image, png, save_asset, sha256
from .catalog import catalog, read_catalog


def ingest_image(db, project_id, data, filename, media_type, attach_reference=False):
    image, orientation = decode_image(data, filename, media_type)
    checksum = sha256(data)
    existing = db.scalar(
        select(ImageAsset).where(
            ImageAsset.project_id == project_id, ImageAsset.input_sha256 == checksum
        )
    )
    if existing:
        return existing, False
    known = next((r for r in catalog() if r["rgb_sha256"] == checksum), None)
    original = save_asset(
        db,
        project_id,
        data,
        "original" + (".jpg" if media_type == "image/jpeg" else ".png"),
        media_type,
    )
    display = save_asset(db, project_id, png(image), "image.png", "image/png")
    thumb = image.copy()
    thumb.thumbnail((320, 240))
    thumbnail = save_asset(db, project_id, png(thumb), "thumbnail.png", "image/png")
    label_id = None
    if known and attach_reference:
        label_data = read_catalog(known, known["label_path"], known["label_sha256"])
        label = Image.open(io.BytesIO(label_data))
        if label.size != image.size:
            raise ValueError("Audited reference grid mismatch")
        label_id = save_asset(db, project_id, label_data, "labels.png", "image/png").id
    result = ImageAsset(
        project_id=project_id,
        name=filename[:180],
        sample_id=known["sample_id"] if known else None,
        split=known["split"] if known else "unassigned",
        input_sha256=checksum,
        width=image.width,
        height=image.height,
        original_asset_id=original.id,
        display_asset_id=display.id,
        thumbnail_asset_id=thumbnail.id,
        label_asset_id=label_id,
        acquired_at=known.get('acquired_at') if known else None,
        transforms={
            'location': known.get('location') if known else None,
            'native_size': known.get('native_size') if known else None,
            'camera': known.get('camera') if known else None,
            "exif_orientation": orientation,
            "normalized": True,
            "origin": "top_left",
            "pixel_center": [0.5, 0.5],
        },
    )
    db.add(result)
    db.flush()
    return result, True
