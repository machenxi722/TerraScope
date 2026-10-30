"""Build a source + prebuilt frontend handoff, excluding credentials and runtime state."""

import hashlib
import json
import argparse
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {
    "backend",
    "frontend",
    "model_service",
    "data",
    "infra",
    "scripts",
    "docs",
    ".github",
    "README.md",
    "compose.yaml",
    ".env.example",
    ".gitignore",
    ".dockerignore",
}
EXCLUDED = {
    "node_modules",
    "runtime",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "test-results",
    "playwright-report",
    "render",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="1.1.0", help="Release version, e.g. 1.1.0")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[a-z0-9.-]+)?", args.version):
        parser.error("version must be a semantic version")
    target = ROOT / f"releases/terrascope-v{args.version}.zip"
    target.parent.mkdir(exist_ok=True)
    files = sorted(
        p
        for p in ROOT.rglob("*")
        if p.is_file()
        and not p.is_symlink()
        and p.relative_to(ROOT).parts[0] in ALLOWED
        and not set(p.relative_to(ROOT).parts) & EXCLUDED
        and p.name not in {".env", ".DS_Store"}
        and p.suffix != ".pyc"
    )
    checksums = {}
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in files:
            relative = str(path.relative_to(ROOT))
            content = path.read_bytes()
            checksums[relative] = hashlib.sha256(content).hexdigest()
            info = zipfile.ZipInfo.from_file(path, arcname="terrascope/" + relative)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content)
        archive.writestr(
            "terrascope/RELEASE-SHA256.json",
            json.dumps(checksums, indent=2, ensure_ascii=False),
        )
    checksum = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix(".zip.sha256").write_text(checksum + "  " + target.name + "\n")
    print(
        f"Packaged {len(files)} files; {target.stat().st_size / 1024**2:.2f} MiB; {target.name}"
    )


if __name__ == "__main__":
    main()
