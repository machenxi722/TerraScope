import hashlib
import io
import json
import shutil
import zipfile

import pytest
from app.config import settings
from app.db import SessionLocal
from app.models import ImageAsset
from app.services.catalog import catalog, checked_json
from app.services.tasks import run_task
from app.services.reports import run_report

BASE = '/api/v1'


@pytest.fixture()
def library(tmp_path, monkeypatch, requires_demo_dataset):
    row = next(r for r in checked_json('manifest.json')['images'] if r['sample_id'] == '7301')
    row = json.loads(json.dumps(row))
    row.update(location={'latitude': 29.618381, 'longitude': -95.721402, 'crs': 'EPSG:4326',
                         'kind': 'camera_position', 'source': 'test fixture'},
               acquired_at='2017:09:03 12:30:00', native_size=[4592, 3072])
    paths = [row['rgb_path'], row['label_path'], *[m['path'] for m in row['masks'].values()]]
    for path in paths:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(settings.demo_dir / path, target)
    data = json.dumps({'images': [row]}).encode()
    (tmp_path / 'manifest.json').write_bytes(data)
    (tmp_path / 'checksums.json').write_text(json.dumps({'manifest.json': hashlib.sha256(data).hexdigest()}))
    monkeypatch.setattr(settings, 'library_dir', tmp_path)
    catalog.cache_clear()
    yield row, tmp_path
    catalog.cache_clear()


def test_library_gps_import_and_frozen_export(client, library):
    summary = client.get(BASE + '/cases/summary?gps_only=true').json()
    assert summary['total'] == summary['gps_count'] == 1
    assert client.get(BASE + '/cases?q=7301&gps_only=true&split=test').json()[0]['location']['longitude'] < 0
    assert client.get(BASE + '/cases?q=7301&split=train').json() == []
    assert client.get(BASE + '/cases?offset=-1').status_code == 422
    assert client.get(BASE + '/cases/7301/thumbnail').headers['content-type'] == 'image/jpeg'
    points = client.get(BASE + '/cases/locations').json()['features']
    assert points[0]['geometry']['coordinates'] == [-95.721402, 29.618381]
    project = client.post(BASE + '/projects', json={'name': 'GPS import'}).json()
    image = client.post(f"{BASE}/projects/{project['id']}/cases/7301").json()
    assert image['native_size'] == [4592, 3072]
    assert image['acquired_at'] == '2017:09:03 12:30:00'
    point = client.get(f"{BASE}/projects/{project['id']}/locations").json()['features'][0]
    assert point['id'] == image['id'] and point['geometry'] == points[0]['geometry']
    task = client.post(BASE + '/analysis-tasks', headers={'Idempotency-Key': 'gps-library-task'},
                       json={'image_id': image['id'], 'strategy': 'tta4'}).json()
    run_task(task['id'])
    task = client.get(BASE + '/analysis-tasks/' + task['id']).json()
    assert task['status'] == 'SUCCEEDED'
    report = client.post(BASE + '/reports', headers={'Idempotency-Key': 'gps-library-report'},
                         json={'prediction_id': task['prediction_id'], 'review_revision': 0}).json()
    # The exported coordinates are taken from the report snapshot, not a later catalogue edit.
    with SessionLocal() as db:
        stored = db.get(ImageAsset, image['id'])
        stored.transforms = {**stored.transforms, 'location': {**stored.transforms['location'], 'latitude': 0}}
        db.commit()
    run_report(report['id'])
    report = client.get(BASE + '/reports/' + report['id']).json()
    assert report['status'] == 'SUCCEEDED', report
    data = client.get(BASE + '/assets/' + report['files']['evidence.zip'] + '/download').content
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        geo = json.loads(archive.read('location.geojson'))
        assert geo['features'][0]['geometry']['coordinates'] == [-95.721402, 29.618381]
        assert 'location.geojson' in archive.read('SHA256SUMS.txt').decode()
    client.post(BASE + '/auth/logout')
    assert client.get(BASE + '/cases/7301/thumbnail').status_code == 401
    assert client.get(f"{BASE}/projects/{project['id']}/locations").status_code == 401


def test_library_corrupt_image_rejected(client, library):
    row, root = library
    (root / row['rgb_path']).write_bytes(b'corrupt')
    project = client.post(BASE + '/projects', json={'name': 'Integrity check'}).json()
    response = client.post(f"{BASE}/projects/{project['id']}/cases/7301")
    assert response.status_code == 422
    assert response.json()['code'] == 'LIBRARY_CHECKSUM'
