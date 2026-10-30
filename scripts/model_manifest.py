"""Create a file hash manifest after independently obtaining and reviewing the base model."""

import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("model_directory", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
root = args.model_directory.resolve()
if args.output.resolve().is_relative_to(root):
    parser.error("Manifest must be stored outside the model directory")
result = {}
for path in sorted(root.rglob("*")):
    if path.is_file() and "__pycache__" not in path.parts:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                digest.update(block)
        result[str(path.relative_to(root))] = digest.hexdigest()
args.output.write_text(json.dumps(result, indent=2))
print(
    f"Recorded {len(result)} files. This manifest records integrity; it does not establish trust in the source."
)
