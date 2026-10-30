"""Run read-only on AutoDL; stream verified experimental assets to stdout as tar."""
import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path

ROOT = Path('/root/autodl-tmp/terrascope')
records = {}
for folder in ['night_20261016', 'holdout370']:
    for row in json.loads((ROOT / folder / 'manifest.json').read_text()):
        row['data_dir'] = str(ROOT / folder / 'data' / row['id'])
        records[row['id']] = row
output = []
with tarfile.open(fileobj=sys.stdout.buffer, mode='w|', dereference=True) as archive:
    for sid, row in sorted(records.items()):
        rgb, label = Path(row['data_dir'])/'RGB.jpg', Path(row['data_dir'])/'labels.png'
        for path, expected in [(rgb,row['rgb_sha256']), (label,row['label_sha256'])]:
            assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, str(path)
            archive.add(path, arcname=f'images/{sid}/{path.name}', recursive=False)
        masks = {}
        for strategy in ['single_view', 'tta4']:
            path = ROOT / 'night_tta_20261016/results/predictions' / strategy / row['split'] / f'{sid}.png'
            if path.is_file():
                dest = f'images/{sid}/{strategy}.png'
                masks[strategy] = {'path':dest, 'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
                archive.add(path, arcname=dest, recursive=False)
        gps=row.get('gps')
        output.append({
            'sample_id':sid, 'split':row['split'], 'width':row['size'][0], 'height':row['size'][1],
            'rgb_path':f'images/{sid}/RGB.jpg', 'rgb_sha256':row['rgb_sha256'],
            'label_path':f'images/{sid}/labels.png', 'label_sha256':row['label_sha256'],
            'model_version':'long_bce_lovasz', 'masks':masks,
            'acquired_at':row.get('capture_time'), 'native_size':row.get('native_size'),
            'camera':(row.get('camera') or '').strip('\x00'),
            'location': {'latitude':gps[0], 'longitude':gps[1], 'crs':'EPSG:4326',
                         'kind':'camera_position', 'source':'FloodNet original EXIF / audited experiment manifest'} if gps else None,
            'provenance':{'manifest':row['data_dir'].split('/')[-3]+'/manifest.json',
                          'original_image':row.get('source_image'),'original_sha256':row.get('raw_sha256')},
        })
    body=json.dumps({'version':'20261018-full','images':output}, ensure_ascii=False, indent=2).encode()
    info=tarfile.TarInfo('manifest.json');info.size=len(body);archive.addfile(info,io.BytesIO(body))
print(f'Exported {len(output)} scenes, {sum(bool(r["location"]) for r in output)} GPS', file=sys.stderr)
