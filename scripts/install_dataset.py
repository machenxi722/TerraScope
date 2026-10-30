"""Validate an AutoDL export and install its library index locally."""
import argparse
import hashlib
import json
import tarfile
from collections import Counter
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('archive',type=Path);args=parser.parse_args()
    dest=ROOT/'data/library';dest.mkdir(exist_ok=True)
    with tarfile.open(args.archive) as archive:
        archive.extractall(dest,filter='data')
    manifest=json.loads((dest/'manifest.json').read_text());checks={}
    for row in manifest['images']:
        for path,sha in [(row['rgb_path'],row['rgb_sha256']),(row['label_path'],row['label_sha256']),*[(m['path'],m['sha256']) for m in row['masks'].values()]]:
            f=dest/path; actual=hashlib.sha256(f.read_bytes()).hexdigest();assert actual==sha,path
            with Image.open(f) as im: assert im.size==(row['width'],row['height']),path
            checks[path]=sha
        loc=row.get('location')
        if loc: assert -90<=loc['latitude']<=90 and -180<=loc['longitude']<=180
        thumb=f"images/{row['sample_id']}/thumbnail.jpg"
        with Image.open(dest/row['rgb_path']) as im:
            im.thumbnail((240,180)); im.save(dest/thumb,quality=85)
        row['thumbnail_path']=thumb;row['thumbnail_sha256']=hashlib.sha256((dest/thumb).read_bytes()).hexdigest();checks[thumb]=row['thumbnail_sha256']
    text=json.dumps(manifest,ensure_ascii=False,indent=2).encode();(dest/'manifest.json').write_bytes(text)
    checks['manifest.json']=hashlib.sha256(text).hexdigest();(dest/'checksums.json').write_text(json.dumps(checks,indent=2))
    summary={'images':len(manifest['images']),'gps':sum(bool(r.get('location')) for r in manifest['images']),
             'splits':dict(Counter(r['split'] for r in manifest['images'])),
             'predictions':sum(len(r['masks']) for r in manifest['images']), 'verified_files':len(checks),
             'manifest_sha256':checks['manifest.json']}
    (ROOT/'docs/evidence/dataset-connection.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
if __name__=='__main__': main()
