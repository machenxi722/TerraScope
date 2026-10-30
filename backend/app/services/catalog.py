import json
from functools import lru_cache
from ..config import settings
from ..errors import require
from .storage import sha256

MODEL_ID = "long_bce_lovasz"
DELTA_SHA = "7c70b717815a39b66c052748c44256b685d17ef1513ee482084ce6419d93dfa8"
PREPROCESS = "terrascope-rgb-v1"


@lru_cache(maxsize=1)
def catalog():
    path = settings.demo_dir / "manifest.json"
    records = {r['sample_id']: r for r in checked_json("manifest.json")["images"]} if path.exists() else {}
    path = settings.library_dir / 'manifest.json'
    if path.exists():
        checks = json.loads((settings.library_dir / 'checksums.json').read_text())
        data = path.read_bytes()
        require(sha256(data) == checks['manifest.json'], 422, 'LIBRARY_CHECKSUM', '实验库索引校验失败')
        for row in json.loads(data)['images']:
            records[row['sample_id']] = {**row, '_library': True}
    return list(records.values())


def read_catalog(record, path, expected_sha):
    if not record.get('_library'):
        return read_demo(path, expected_sha)
    root = settings.library_dir.resolve()
    target = (root / path).resolve()
    require(target.is_relative_to(root) and target.is_file(), 422, 'LIBRARY_MISSING', '实验影像文件缺失')
    data = target.read_bytes()
    require(sha256(data) == expected_sha, 422, 'LIBRARY_CHECKSUM', '实验影像校验失败')
    return data


def checked_json(relative):
    checksums = json.loads((settings.demo_dir / "checksums.json").read_text())
    require(relative in checksums, 422, "DEMO_CHECKSUM", "资料未登记在校验清单中")
    return json.loads(read_demo(relative, checksums[relative]))


def match_image(image):
    return next(
        (
            r
            for r in catalog()
            if r["rgb_sha256"] == image.input_sha256
            and r["split"] == image.split
            and r["width"] == image.width
            and r["height"] == image.height
        ),
        None,
    )


def read_demo(path, expected_sha):
    target = (settings.demo_dir / path).resolve()
    require(
        target.is_relative_to(settings.demo_dir.resolve()) and target.is_file(),
        422,
        "DEMO_MISSING",
        "案例资产缺失",
    )
    data = target.read_bytes()
    require(sha256(data) == expected_sha, 422, "DEMO_CHECKSUM", "案例资产摘要不一致")
    return data


def historical_mask(image, config):
    record = match_image(image)
    require(
        record
        and config["model_version"] == record["model_version"]
        and config["strategy"] in record["masks"],
        422,
        "NO_HISTORICAL_MATCH",
        "该影像没有匹配的历史结果；请接入真实推理服务或导入外部结果",
    )
    mask = record["masks"][config["strategy"]]
    return read_catalog(record, mask["path"], mask["sha256"])
