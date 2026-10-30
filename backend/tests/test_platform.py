import hashlib
import io
import json
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from app.main import app
from app.db import SessionLocal
from app.models import AnalysisTask, Prediction, User, Project, ProjectMember, AssetFile
from app.errors import DomainError
from app.security import hash_password
from app.services.metrics import calculate, summarize
from app.services.storage import png, read_mask
from app.services.tasks import run_task
from app.services.reports import run_report

BASE = "/api/v1"


def submit(client, image, key="task-idempotency-0001", strategy="tta4"):
    response = client.post(
        BASE + "/analysis-tasks",
        headers={"Idempotency-Key": key},
        json={"image_id": image["id"], "strategy": strategy},
    )
    assert response.status_code == 202, response.text
    return response.json()


def execute(client, image):
    task = submit(client, image)
    run_task(task["id"])
    task = client.get(BASE + "/analysis-tasks/" + task["id"]).json()
    assert task["status"] == "SUCCEEDED", task
    return client.get(BASE + "/predictions/" + task["prediction_id"]).json()


def test_real_7301_complete_flow(client, demo):
    project, images = demo
    pred = execute(client, images["7301"])
    assert pred["metrics"]["pred_pixels"] == 152585
    assert pred["metrics"]["valid_pixels"] == 701440
    assert pred["metrics"]["coverage_percent"] == pytest.approx(21.753107892335766)
    assert pred["evaluation"]["tp"] == 140651
    assert pred["evaluation"]["fp"] == 11934
    assert pred["evaluation"]["fn"] == 39168
    assert pred["contract"]["source_mode"] == "historical_replay"
    assert pred["contract"]["coordinate_mode"] == "pixel"
    body = {
        "base_revision": 0,
        "decision": "confirmed",
        "note": "已核验道路边界，局部需现场调查。",
        "annotations": [
            {
                "type": "Polygon",
                "coordinates": [[0, 0], [1024, 0], [1024, 685], [0, 685], [0, 0]],
            }
        ],
    }
    saved = client.post(f"{BASE}/predictions/{pred['id']}/reviews", json=body)
    assert saved.status_code == 201, saved.text
    assert (
        client.post(f"{BASE}/predictions/{pred['id']}/reviews", json=body).status_code
        == 409
    )
    refreshed = client.get(f"{BASE}/predictions/{pred['id']}").json()
    assert (
        refreshed["review_revision"] == 1
        and refreshed["reviews"][0]["note"] == body["note"]
    )
    report = client.post(
        BASE + "/reports",
        headers={"Idempotency-Key": "report-snapshot-0001"},
        json={"prediction_id": pred["id"], "review_revision": 1},
    )
    assert report.status_code == 202, report.text
    rid = report.json()["id"]
    # Later review must not change an earlier export snapshot.
    body.update(base_revision=1, note="第二版复核", decision="needs_investigation")
    assert (
        client.post(f"{BASE}/predictions/{pred['id']}/reviews", json=body).status_code
        == 201
    )
    run_report(rid)
    report = client.get(BASE + "/reports/" + rid).json()
    assert report["status"] == "SUCCEEDED", report
    assert report["snapshot"]["review_revision"] == 1
    archive = client.get(
        BASE + "/assets/" + report["files"]["evidence.zip"] + "/download"
    )
    assert archive.status_code == 200
    with zipfile.ZipFile(io.BytesIO(archive.content)) as z:
        assert z.read("report.pdf").startswith(b"%PDF")
        assert b"/FontFile2" in z.read("report.pdf")  # embedded offline Chinese font
        snap = json.loads(z.read("metadata.json"))
        assert snap["review"]["note"] == "已核验道路边界，局部需现场调查。"
        assert snap["prediction"]["review_revision"] == 1
        assert (
            hashlib.sha256(z.read("input.jpg")).hexdigest()
            == pred["contract"]["input_sha256"]
        )
        mask = np.asarray(Image.open(io.BytesIO(z.read("mask.png"))))
        assert int((mask > 0).sum()) == 152585
        for line in z.read("SHA256SUMS.txt").decode().splitlines():
            checksum, name = line.split("  ")
            assert hashlib.sha256(z.read(name)).hexdigest() == checksum


def test_no_gt_upload_and_manual_import(client):
    project = client.post(BASE + "/projects", json={"name": "未知影像"}).json()
    rgb = png(Image.new("RGB", (10, 6), (12, 34, 56)))
    upload = client.post(
        f"{BASE}/projects/{project['id']}/images",
        files={"file": ("new.png", rgb, "image/png")},
    )
    assert upload.status_code == 201
    image = upload.json()
    duplicate = client.post(
        f"{BASE}/projects/{project['id']}/images",
        files={"file": ("renamed.png", rgb, "image/png")},
    )
    assert duplicate.json()["id"] == image["id"]
    response = client.post(
        BASE + "/analysis-tasks",
        headers={"Idempotency-Key": "unknown-image-key"},
        json={"image_id": image["id"]},
    )
    assert (
        response.status_code == 422 and response.json()["code"] == "NO_HISTORICAL_MATCH"
    )
    response = client.post(
        BASE + "/analysis-tasks",
        headers={"Idempotency-Key": "gpu-missing-key"},
        json={"image_id": image["id"], "mode": "live_inference"},
    )
    assert response.status_code == 503
    mask = np.zeros((6, 10), dtype=np.uint8)
    mask[2:4, 4:8] = 255
    data = png(Image.fromarray(mask))
    meta = {
        "input_sha256": image["input_sha256"],
        "mask_sha256": hashlib.sha256(data).hexdigest(),
        "width": 10,
        "height": 6,
        "model_version": "external-test",
        "strategy": "single_view",
        "preprocess_version": "external-v1",
        "source": "测试来源",
    }
    response = client.post(
        f"{BASE}/images/{image['id']}/import-result",
        headers={"Idempotency-Key": "import-result-key"},
        files={"mask": ("mask.png", data, "image/png")},
        data={"metadata": json.dumps(meta)},
    )
    assert response.status_code == 202, response.text
    run_task(response.json()["id"])
    pred = client.get(f"{BASE}/predictions?image_id={image['id']}").json()[0]
    assert pred["metrics"]["pred_pixels"] == 8 and pred["metrics"]["valid_pixels"] == 60
    assert pred["evaluation"] is None and pred["difference_asset_id"] is None
    assert pred["contract"]["model_verified"] is False
    pixel = client.get(f"{BASE}/predictions/{pred['id']}/pixel?x=4&y=2").json()
    assert pixel["predicted"] is True and pixel["rgb"] == [12, 34, 56]
    assert (
        client.get(f"{BASE}/predictions/{pred['id']}/pixel?x=10&y=2").status_code == 422
    )


def test_idempotency_cancel_retry_recovery(client, demo):
    _, images = demo
    task = submit(client, images["7301"])
    assert submit(client, images["7301"])["id"] == task["id"]
    conflict = client.post(
        BASE + "/analysis-tasks",
        headers={"Idempotency-Key": "task-idempotency-0001"},
        json={"image_id": images["7461"]["id"]},
    )
    assert conflict.status_code == 409
    assert (
        client.post(f"{BASE}/analysis-tasks/{task['id']}/cancel").json()["status"]
        == "CANCELED"
    )
    run_task(task["id"])
    retry = client.post(
        f"{BASE}/analysis-tasks/{task['id']}/retry",
        headers={"Idempotency-Key": "retry-task-unique-key"},
    ).json()
    assert retry["attempt"] == 2 and retry["parent_id"] == task["id"]
    with SessionLocal() as db:
        stale = db.get(AnalysisTask, retry["id"])
        stale.status, stale.lease_until, stale.lease_token = (
            "POSTPROCESSING",
            time.time() - 1,
            "lost-worker",
        )
        db.commit()
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(run_task, [retry["id"], retry["id"]]))
    run_task(retry["id"])
    with SessionLocal() as db:
        assert db.get(AnalysisTask, retry["id"]).status == "SUCCEEDED"
        assert db.scalar(select(func.count()).select_from(Prediction)) == 1


def test_active_cancel_and_file_corruption(client, demo):
    _, images = demo
    task = submit(client, images["7301"])
    with SessionLocal() as db:
        t = db.get(AnalysisTask, task["id"])
        t.status = "CANCEL_REQUESTED"
        db.commit()
    run_task(task["id"])
    assert (
        client.get(f"{BASE}/analysis-tasks/{task['id']}").json()["status"] == "CANCELED"
    )
    task = submit(client, images["7301"], key="file-corruption-key")
    with SessionLocal() as db:
        asset = db.get(AssetFile, images["7301"]["display_asset_id"])
        asset.sha256 = "0" * 64
        db.commit()
    run_task(task["id"])
    failed = client.get(f"{BASE}/analysis-tasks/{task['id']}").json()
    assert failed["status"] == "FAILED" and failed["error"]["code"] == "ASSET_CHECKSUM"


def test_permissions_csrf_archive(client, demo):
    project, images = demo
    pred = execute(client, images["7301"])
    with SessionLocal() as db:
        user = User(
            username="viewer", password_hash=hash_password("viewer-password-123")
        )
        db.add(user)
        db.commit()
        user_id = user.id
    with TestClient(app) as outsider:
        login = outsider.post(
            BASE + "/auth/login",
            json={"username": "viewer", "password": "viewer-password-123"},
        )
        outsider.headers["X-CSRF-Token"] = login.json()["csrf_token"]
        for path in [
            f"/images/{images['7301']['id']}",
            f"/predictions/{pred['id']}",
            f"/assets/{pred['mask_asset_id']}/download",
            f"/projects/{project['id']}/images",
        ]:
            assert outsider.get(BASE + path).status_code == 403
        assert outsider.get(BASE + "/projects").json() == []
        with SessionLocal() as db:
            db.add(
                ProjectMember(project_id=project["id"], user_id=user_id, role="viewer")
            )
            db.commit()
        assert outsider.get(f"{BASE}/predictions/{pred['id']}").status_code == 200
        assert (
            outsider.post(
                BASE + "/analysis-tasks",
                headers={"Idempotency-Key": "viewer-action-key"},
                json={"image_id": images["7301"]["id"]},
            ).status_code
            == 403
        )
        assert (
            outsider.post(
                f"{BASE}/predictions/{pred['id']}/reviews",
                json={"base_revision": 0, "decision": "confirmed", "note": "test"},
            ).status_code
            == 403
        )
        outsider.headers.pop("X-CSRF-Token")
        assert (
            outsider.post(BASE + "/projects", json={"name": "CSRF"}).status_code == 403
        )
    archived = client.patch(
        f"{BASE}/projects/{project['id']}",
        json={"name": project["name"], "archived": True},
    )
    assert archived.status_code == 200
    assert (
        client.post(
            BASE + "/analysis-tasks",
            headers={"Idempotency-Key": "archive-task-key"},
            json={"image_id": images["7301"]["id"]},
        ).status_code
        == 409
    )
    assert client.get(f"{BASE}/predictions/{pred['id']}").status_code == 200


def test_upload_and_polygon_validation(client, demo):
    project, images = demo
    for filename, data, mime in [
        ("bad.png", b"not a PNG", "image/png"),
        ("active.svg", b"<svg/>", "image/svg+xml"),
        ("wrong.png", png(Image.new("RGB", (3, 3))), "image/jpeg"),
    ]:
        assert (
            client.post(
                f"{BASE}/projects/{project['id']}/images",
                files={"file": (filename, data, mime)},
            ).status_code
            == 422
        )
    pred = execute(client, images["7301"])
    response = client.post(
        f"{BASE}/predictions/{pred['id']}/reviews",
        json={
            "base_revision": 0,
            "decision": "confirmed",
            "note": "越界",
            "annotations": [{"coordinates": [[0, 0], [1025, 0], [0, 685], [0, 0]]}],
        },
    )
    assert response.status_code == 422
    with pytest.raises(DomainError):
        read_mask(png(Image.new("L", (8, 9))), 10, 10)
    with pytest.raises(DomainError):
        read_mask(png(Image.new("L", (10, 10), 100)), 10, 10)


def test_metrics_empty_validity_and_partition_contract(client, demo):
    project, _ = demo
    mask = np.zeros((2, 2), dtype=bool)
    metric, evaluation = calculate(mask, np.zeros((2, 2), dtype=np.uint8))
    assert (
        metric["coverage_percent"] == 0
        and evaluation["iou"] is None
        and evaluation["recall"] is None
    )
    with pytest.raises(DomainError):
        calculate(mask, np.full((2, 2), 255))
    mask[0, 0] = True
    metric, evaluation = calculate(mask, np.array([[255, 0], [3, 0]]))
    assert (
        metric["pred_pixels"] == 0
        and metric["valid_pixels"] == 3
        and evaluation["fn"] == 1
    )
    test = client.get(
        f"{BASE}/experiments/floodnet/metrics?project_id={project['id']}&split=test"
    ).json()
    holdout = client.get(
        f"{BASE}/experiments/floodnet/metrics?project_id={project['id']}&split=holdout"
    ).json()
    assert test["summary"]["n"] == 448 and holdout["summary"]["n"] == 370
    assert test["summary"]["global_iou"] == pytest.approx(0.5827679429196668)
    assert holdout["summary"]["global_iou"] == pytest.approx(0.5568506151575942)
    assert any(
        r["availability"] == "statistics_only" and r["image_id"] is None
        for r in test["records"]
    )


def test_login_rate_limit_and_revocation(client):
    with TestClient(app) as c:
        for _ in range(10):
            assert (
                c.post(
                    BASE + "/auth/login",
                    json={"username": "missing-user", "password": "incorrect"},
                ).status_code
                == 401
            )
        assert (
            c.post(
                BASE + "/auth/login",
                json={"username": "missing-user", "password": "incorrect"},
            ).status_code
            == 429
        )
    assert client.post(BASE + "/auth/logout").status_code == 204
    assert client.get(BASE + "/projects").status_code == 401


def test_upload_resource_limits(client, monkeypatch):
    from app.config import settings

    project = client.post(BASE + "/projects", json={"name": "上传边界"}).json()
    image = png(Image.new("RGB", (3, 3)))
    monkeypatch.setattr(settings, "max_pixels", 5)
    response = client.post(
        f"{BASE}/projects/{project['id']}/images",
        files={"file": ("pixels.png", image, "image/png")},
    )
    assert response.status_code == 413 and response.json()["code"] == "PIXEL_LIMIT"
    monkeypatch.setattr(settings, "max_pixels", 100)
    monkeypatch.setattr(settings, "max_upload_bytes", 16)
    response = client.post(
        f"{BASE}/projects/{project['id']}/images",
        files={"file": ("bytes.png", image, "image/png")},
    )
    assert response.status_code == 413 and response.json()["code"] == "UPLOAD_TOO_LARGE"
