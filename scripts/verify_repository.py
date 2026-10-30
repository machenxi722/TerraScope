"""Verify published files after git lfs pull; no dataset or GPU required."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--weights-only', action='store_true')
    args = parser.parse_args()
    if args.weights_only:
        entries = {'weights/long_bce_lovasz_seed20261017_best_delta.pt':
                   '7c70b717815a39b66c052748c44256b685d17ef1513ee482084ce6419d93dfa8'}
    else:
        entries = json.loads((ROOT / 'docs/repository/file-manifest.json').read_text())['sha256']
    failures = []
    for name, expected in entries.items():
        path = ROOT / name
        if not path.is_file() or digest(path) != expected:
            failures.append(name)
    if failures:
        for name in failures:
            print('MISSING OR CHANGED:', name)
        raise SystemExit('Verification failed. Run git lfs pull and check local changes.')
    print(f'Verified {len(entries)} files (SHA256).')


if __name__ == '__main__':
    main()
