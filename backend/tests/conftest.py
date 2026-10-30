import os
import json
import tempfile
from pathlib import Path
import pytest

TEST_ROOT = Path(tempfile.mkdtemp(prefix="terrascope-test-"))
os.environ["TERRA_DATABASE_URL"] = os.environ.get(
    "TERRA_TEST_DATABASE_URL"
) or "sqlite:///" + str(TEST_ROOT / "test.db")
os.environ["TERRA_STORAGE_DIR"] = str(TEST_ROOT / "assets")
os.environ["TERRA_ADMIN_PASSWORD"] = "test-password-for-tests"
os.environ["TERRA_MODEL_SERVICE_URL"] = ""
os.environ["TERRA_MODEL_SERVICE_TOKEN"] = ""
os.environ["TERRA_LIBRARY_DIR"] = str(TEST_ROOT / 'library')

from fastapi.testclient import TestClient
from app.db import Base, engine, SessionLocal
from app.main import app
from app.services.seed import init_admin, seed_demo
from app.config import settings


@pytest.fixture()
def requires_demo_dataset():
    manifest = settings.demo_dir / "manifest.json"
    if not manifest.exists() or not json.loads(manifest.read_text())["images"]:
        pytest.skip("Real dataset excluded from Git; set TERRA_DEMO_DIR to the validated local demo bundle")


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        user = init_admin(db)
        db.commit()
    with TestClient(app) as c:
        login = c.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "test-password-for-tests"},
        )
        assert login.status_code == 200, login.text
        c.headers["X-CSRF-Token"] = login.json()["csrf_token"]
        yield c


@pytest.fixture()
def demo(client, requires_demo_dataset):
    p = client.post("/api/v1/system/demo")
    assert p.status_code == 201, p.text
    project = p.json()
    images = client.get(f"/api/v1/projects/{project['id']}/images").json()
    return project, {i["sample_id"]: i for i in images}
