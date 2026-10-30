import hashlib
import json

from app.config import settings
from app.services.catalog import catalog


def test_empty_catalogue_supports_projects_and_experiment_statistics(client, tmp_path, monkeypatch):
    # Use real stored aggregate results, but no dataset images or labels.
    demo = tmp_path / "demo"
    demo.mkdir()
    (demo / "manifest.json").write_text('{"images": []}')
    checks = {"manifest.json": hashlib.sha256((demo / "manifest.json").read_bytes()).hexdigest()}
    (demo / "checksums.json").write_text(json.dumps(checks))
    monkeypatch.setattr(settings, "demo_dir", demo)
    catalog.cache_clear()
    try:
        assert client.get("/api/v1/cases").json() == []
        caps = client.get("/api/v1/system/capabilities").json()
        assert caps["historical_replay"]["available"] is False
        response = client.post("/api/v1/system/demo")
        assert response.status_code == 409
        assert response.json()["code"] == "DATASET_REQUIRED"
        project = client.post("/api/v1/projects", json={"name": "No dataset"})
        assert project.status_code == 201
    finally:
        catalog.cache_clear()


def test_published_statistics_remain_readable_without_images(client):
    project = client.post("/api/v1/projects", json={"name": "Statistics only"}).json()
    for split, count in [("test", 448), ("holdout", 370), ("val", 80)]:
        response = client.get("/api/v1/experiments/floodnet/metrics", params={"project_id": project["id"], "split": split})
        assert response.status_code == 200
        assert response.json()["total"] == count
