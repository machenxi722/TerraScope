"""Download only official model / Sen1Floods11 inputs, with resumable file-level IO."""
import argparse
import concurrent.futures
import time
import urllib.request
from pathlib import Path

from .common import HF_REPO, HF_REVISION, write_json
from .data import official_rows


def get_file(url, path):
    path = Path(path)
    if path.exists() and path.stat().st_size > 0:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".part")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=180) as response, open(temp, "wb") as f:
                while block := response.read(1024 * 1024):
                    f.write(block)
            temp.replace(path)
            return
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("what", choices=["model", "data"])
    p.add_argument("--out", required=True)
    p.add_argument("--workers", type=int, default=4)
    a = p.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.what == "model":
        from huggingface_hub import snapshot_download
        snapshot_download(repo_id=HF_REPO, revision=HF_REVISION, local_dir=str(out),
                           allow_patterns=["*.json", "*.py", "*.txt", "*.safetensors", "*.model", "LICENSE*", "README.md"],
                           max_workers=a.workers)
        write_json(out / "download_provenance.json", {"repo": HF_REPO, "revision": HF_REVISION})
    else:
        root = "https://storage.googleapis.com/sen1floods11/v1.1/data/flood_events/HandLabeled"
        jobs = []
        for row in official_rows():
            for folder, name in [("S2Hand", row["s2"]), ("LabelHand", row["label"])]:
                jobs.append((f"{root}/{folder}/{name}", out / folder / name))
        with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
            futures = [pool.submit(get_file, url, path) for url, path in jobs]
            for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
                future.result()
                if i % 20 == 0:
                    print(f"downloaded / already present {i}/{len(jobs)}", flush=True)
        write_json(out / "download_provenance.json", {"root": root, "files": len(jobs),
                                                     "splits": "bundled official v1.1 CSVs"})


if __name__ == "__main__":
    main()
