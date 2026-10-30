import hashlib
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HF_REPO = "sy1998/TerraScope"
HF_REVISION = "a2333262586f8a07238d85db85061979198435fc"
PROMPT = "<image>\nSegment all visible surface water in this satellite image."
PREFIX = "Water [SEG]"
PROTOCOL = "water-fixed-prefix-multimask-v1"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    temp.replace(path)


def verify_sources():
    for name, expected in read_json(ROOT / "source_lock.json")["files"].items():
        if sha256(ROOT / name) != expected:
            raise ValueError(f"Pinned source changed: {name}")


def load_manifest(path):
    path = Path(path).resolve()
    obj = read_json(path)
    rows = obj["samples"]
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate sample IDs / split leakage")
    for row in rows:
        for key in ("image", "target"):
            row[key] = str((path.parent / row[key]).resolve())
    return obj


def atomic_torch_save(obj, path):
    import torch
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    torch.save(obj, temp)
    temp.replace(path)


def load_tensor_file(path):
    import torch
    return torch.load(path, map_location="cpu", weights_only=True)


def deadline(hours):
    end = time.time() + hours * 3600
    global_end = os.environ.get("TSFT_DEADLINE")
    return min(end, float(global_end)) if global_end else end


def check_deadline(end, reserve=30):
    if time.time() + reserve >= end:
        raise TimeoutError("Time budget reached; no further work scheduled")
