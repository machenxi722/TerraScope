"""Read-only AutoDL inventory; run with the server's existing Python interpreter."""

import hashlib
import importlib.metadata
import json
import shutil
import subprocess
import sys
from pathlib import Path


def main():
    root = Path("/root/autodl-tmp/terrascope")
    result = {
        "python": sys.executable,
        "python_version": sys.version,
        "project_exists": root.is_dir(),
        "disk": shutil.disk_usage("/root/autodl-tmp")._asdict(),
    }
    result["packages"] = {}
    for name in [
        "torch",
        "transformers",
        "accelerate",
        "xtuner",
        "peft",
        "mmengine",
        "mmdet",
        "timm",
        "fastapi",
        "uvicorn",
        "pydantic",
        "python-multipart",
        "Pillow",
    ]:
        try:
            result["packages"][name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result["packages"][name] = None
    if shutil.which("nvidia-smi"):
        try:
            gpu = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total,driver_version",
                    "--format=csv,noheader",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            result["gpu"] = gpu.stdout.strip()
        except OSError:
            result["gpu"] = "unavailable (CPU-only instance mode)"
    result["conda_environments"] = [
        str(p) for p in Path("/root/miniconda3/envs").glob("*/bin/python")
    ]
    if root.is_dir():
        result["top_level"] = sorted(p.name for p in root.iterdir())
        base = root / "models/TerraScope"
        result["base_files"] = [
            {"path": str(p.relative_to(base)), "bytes": p.stat().st_size}
            for p in sorted(base.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts
        ]
        checkpoints = list(root.rglob("long_bce_lovasz_seed20261017_best_delta.pt"))
        result["deltas"] = []
        for p in checkpoints:
            h = hashlib.sha256()
            with p.open("rb") as stream:
                for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                    h.update(block)
            result["deltas"].append(
                {"path": str(p), "bytes": p.stat().st_size, "sha256": h.hexdigest()}
            )
        result["protocols"] = [str(p) for p in root.rglob("protocol.json")]
        result["reference_7301"] = [
            str(p) for p in root.rglob("*7301*") if p.is_file()
        ][:60]
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
