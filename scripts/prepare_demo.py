"""Copy only audited examples and final experiment records, checking every source hash."""

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "TerraScope_队友Codex接续资料_20261016"
DEST = ROOT / "data/demo"
AUDIT = ROOT.parent / "方案设计/资料审阅与案例资产核验.json"


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    records = []
    result_dir = (
        SOURCE / "04_素材与源码/workspace/work/night_20261016/tta_backup/results"
    )
    for item in json.loads(AUDIT.read_text())["案例资产"]:
        sid = item["sample_id"]
        folder = DEST / "images" / sid
        folder.mkdir(parents=True, exist_ok=True)
        source = SOURCE / item["rgb_path"]
        assert checksum(source) == item["rgb_sha256"]
        shutil.copy2(source, folder / "RGB.jpg")
        shutil.copy2(SOURCE / item["label_path"], folder / "labels.png")
        masks = {}
        for strategy in ["single_view", "tta4"]:
            path = result_dir / "predictions" / strategy / item["split"] / f"{sid}.png"
            if path.exists():
                shutil.copy2(path, folder / f"{strategy}.png")
                if strategy == "tta4":
                    assert checksum(path) == item["prediction_sha256"]
                masks[strategy] = {
                    "path": f"images/{sid}/{strategy}.png",
                    "sha256": checksum(path),
                }
        records.append(
            {
                "sample_id": sid,
                "split": item["split"],
                "width": item["width"],
                "height": item["height"],
                "rgb_path": f"images/{sid}/RGB.jpg",
                "rgb_sha256": item["rgb_sha256"],
                "label_path": f"images/{sid}/labels.png",
                "label_sha256": checksum(folder / "labels.png"),
                "model_version": "long_bce_lovasz",
                "masks": masks,
            }
        )
    exp = DEST / "experiments"
    exp.mkdir(exist_ok=True)
    for strategy in ["single_view", "tta4"]:
        for split in ["test", "holdout", "val"]:
            shutil.copy2(result_dir / f"{strategy}_{split}.json", exp)
    shutil.copy2(SOURCE / "03_实验结果/当前汇报主要指标.json", exp / "baselines.json")
    (DEST / "manifest.json").write_text(
        json.dumps(
            {"version": "20261016", "images": records}, indent=2, ensure_ascii=False
        )
    )
    checksums = {
        str(p.relative_to(DEST)): checksum(p)
        for p in DEST.rglob("*")
        if p.is_file() and p.name != "checksums.json"
    }
    (DEST / "checksums.json").write_text(json.dumps(checksums, indent=2))
    print(f"Prepared {len(records)} audited examples and {len(checksums)} files")


if __name__ == "__main__":
    main()
