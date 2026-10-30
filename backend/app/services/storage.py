import hashlib
import io
import os
import warnings
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError
from ..config import settings
from ..errors import DomainError, require
from ..models import AssetFile, uid


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def png(image):
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def decode_image(data, filename, media_type):
    require(
        len(data) <= settings.max_upload_bytes,
        413,
        "UPLOAD_TOO_LARGE",
        "文件超过 20 MB 限制",
    )
    ext = Path(filename or "").suffix.lower()
    require(
        ext in {".jpg", ".jpeg", ".png"}, 422, "IMAGE_FORMAT", "仅支持 JPG、PNG 影像"
    )
    expected = "PNG" if ext == ".png" else "JPEG"
    require(
        media_type == ("image/png" if expected == "PNG" else "image/jpeg"),
        422,
        "IMAGE_MIME",
        "扩展名与内容类型不匹配",
    )
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            im = Image.open(io.BytesIO(data))
            require(
                im.format == expected and getattr(im, "n_frames", 1) == 1,
                422,
                "IMAGE_FORMAT",
                "图像格式不匹配或包含多个帧",
            )
            require(
                im.width * im.height <= settings.max_pixels,
                413,
                "PIXEL_LIMIT",
                "图像像素数超过限制",
            )
            orientation = int(im.getexif().get(274, 1))
            im.load()
            return ImageOps.exif_transpose(im).convert("RGB"), orientation
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        raise DomainError(422, "IMAGE_DECODE", "文件无法解码为安全有效的图像")


def read_mask(data, width, height):
    require(
        len(data) <= settings.max_upload_bytes, 413, "UPLOAD_TOO_LARGE", "掩膜文件过大"
    )
    try:
        with Image.open(io.BytesIO(data)) as im:
            require(
                im.format == "PNG" and im.mode in {"L", "1", "P"},
                422,
                "MASK_FORMAT",
                "掩膜必须是单通道二值 PNG",
            )
            require(
                im.size == (width, height),
                422,
                "GRID_MISMATCH",
                "掩膜尺寸必须与原图完全一致",
            )
            arr = np.asarray(im).copy()
    except (UnidentifiedImageError, OSError, ValueError):
        raise DomainError(422, "MASK_DECODE", "掩膜无法解码")
    require(
        set(np.unique(arr).tolist()) <= {0, 1, 255},
        422,
        "MASK_VALUES",
        "二值掩膜只允许 0/1 或 0/255",
    )
    require(
        not (1 in arr and 255 in arr),
        422,
        "MASK_VALUES",
        "不得混用 1 和 255 的前景编码",
    )
    return arr > 0


def asset_path(asset):
    path = (settings.storage_dir / asset.path).resolve()
    require(
        path.is_relative_to(settings.storage_dir.resolve()),
        404,
        "ASSET_NOT_FOUND",
        "资产不存在",
    )
    return path


def read_asset(db, asset_id):
    asset = db.get(AssetFile, asset_id)
    require(asset, 404, "ASSET_NOT_FOUND", "资产不存在")
    path = asset_path(asset)
    require(path.is_file(), 422, "ASSET_MISSING", "资产文件缺失，请恢复备份")
    data = path.read_bytes()
    require(sha256(data) == asset.sha256, 422, "ASSET_CHECKSUM", "资产摘要校验失败")
    return data


def save_asset(db, project_id, data, filename, media_type):
    asset_id = uid()
    relative = f"{project_id}/{asset_id}"
    target = settings.storage_dir / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(".tmp")
    with temp.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, target)
    asset = AssetFile(
        id=asset_id,
        project_id=project_id,
        path=relative,
        sha256=sha256(data),
        size_bytes=len(data),
        media_type=media_type,
        filename=filename,
    )
    db.add(asset)
    db.flush()
    return asset
