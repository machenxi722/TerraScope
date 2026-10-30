"""API connections used by search, experiment drill-down, membership and deep links."""

import csv
import io

from app.db import SessionLocal
from app.main import app
from app.models import AnalysisTask, ImageAsset, Prediction
from app.services.tasks import run_task
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_platform import BASE, submit


def test_image_search_matches_sample_and_name_without_wildcards(client, demo):
    project, images = demo
    with SessionLocal() as db:
        db.get(ImageAsset, images["7301"]["id"]).name = "RoadSurvey.JPG"
        db.commit()
    for q in ["7301", "roadsurvey"]:
        rows = client.get(
            f"{BASE}/projects/{project['id']}/images", params={"q": q}
        ).json()
        assert [r["id"] for r in rows] == [images["7301"]["id"]]
    assert client.get(f"{BASE}/projects/{project['id']}/images?q=%25").json() == []


def test_experiment_drilldown_and_full_filtered_csv(client, requires_demo_dataset):
    project = client.post(BASE + "/projects", json={"name": "实验记录"}).json()
    params = {
        "project_id": project["id"],
        "split": "test",
        "strategy": "single_view",
        "q": "7301",
    }
    endpoint = BASE + "/experiments/floodnet"
    row = client.get(endpoint + "/metrics", params=params).json()["records"][0]
    assert (
        row["case_available"]
        and row["image_id"] is None
        and row["prediction_id"] is None
    )
    image = client.post(f"{BASE}/projects/{project['id']}/cases/7301").json()
    single = submit(client, image, "single-view-deeplink", "single_view")
    run_task(single["id"])
    tta = submit(client, image, "tta-view-deeplink", "tta4")
    run_task(tta["id"])
    row = client.get(endpoint + "/metrics", params=params).json()["records"][0]
    pred_id = client.get(f"{BASE}/analysis-tasks/{single['id']}").json()[
        "prediction_id"
    ]
    assert row["prediction_id"] == pred_id and row["image_id"] == image["id"]
    filtered = client.get(endpoint + "/export", params=params)
    assert filtered.status_code == 200
    rows = list(csv.DictReader(io.StringIO(filtered.content.decode("utf-8-sig"))))
    assert len(rows) == 1 and rows[0]["sample_id"] == "7301"
    assert rows[0]["strategy"] == "single_view" and rows[0]["pred_pixels"] == "147010"
    for split, expected in [("test", 448), ("holdout", 370), ("val", 80)]:
        response = client.get(
            endpoint + "/export", params={**params, "q": "", "split": split}
        )
        exported = list(
            csv.DictReader(io.StringIO(response.content.decode("utf-8-sig")))
        )
        assert len(exported) == expected
        assert all(r["split"] == split for r in exported)
    assert (
        client.get(
            endpoint + "/export", params={**params, "project_id": "missing"}
        ).status_code
        == 404
    )


def test_prediction_pagination_reaches_old_results(client, demo):
    _, images = demo
    task = submit(client, images["7301"])
    run_task(task["id"])
    with SessionLocal() as db:
        pred = db.scalar(select(Prediction))
        values = {
            c.name: getattr(pred, c.name)
            for c in Prediction.__table__.columns
            if c.name not in {"id", "task_id", "created_at"}
        }
        original_task = db.get(AnalysisTask, task["id"])
        task_values = {
            c.name: getattr(original_task, c.name)
            for c in AnalysisTask.__table__.columns
            if c.name not in {"id", "idempotency_key"}
        }
        for i in range(102):
            duplicate = AnalysisTask(**task_values, idempotency_key=f"pagination-{i}")
            db.add(duplicate)
            db.flush()
            db.add(
                Prediction(
                    **values, task_id=duplicate.id, created_at=pred.created_at + i + 1
                )
            )
        db.commit()
    params = {"image_id": images["7301"]["id"], "limit": 100}
    page1 = client.get(BASE + "/predictions", params=params).json()
    page2 = client.get(BASE + "/predictions", params={**params, "offset": 100}).json()
    assert len(page1) == 100 and len(page2) == 3
    assert not {r["id"] for r in page1} & {r["id"] for r in page2}


def test_member_removal_revokes_access_and_preserves_project_admin(client, demo):
    project, _ = demo
    created = client.post(
        BASE + "/users",
        json={"username": "reader", "password": "reader-pass-for-tests"},
    ).json()
    endpoint = f"{BASE}/projects/{project['id']}/members"
    assert (
        client.put(endpoint, json={"username": "reader", "role": "viewer"}).status_code
        == 200
    )
    with TestClient(app) as reader:
        login = reader.post(
            BASE + "/auth/login",
            json={"username": "reader", "password": "reader-pass-for-tests"},
        ).json()
        reader.headers["X-CSRF-Token"] = login["csrf_token"]
        assert reader.get(f"{BASE}/projects/{project['id']}/images").status_code == 200
        assert reader.delete(endpoint + "/" + created["id"]).status_code == 403
        assert client.delete(endpoint + "/" + created["id"]).status_code == 204
        assert reader.get(f"{BASE}/projects/{project['id']}/images").status_code == 403
        assert (
            reader.get(
                BASE + "/experiments/floodnet/export",
                params={"project_id": project["id"]},
            ).status_code
            == 403
        )
    me = client.get(BASE + "/auth/me").json()["user"]
    assert client.delete(endpoint + "/" + me["id"]).status_code == 409
    # System administrators must also leave one explicit project administrator.
    client.put(endpoint, json={"username": "reader", "role": "admin"})
    with SessionLocal() as db:
        from app.models import ProjectMember

        db.delete(db.get(ProjectMember, (project["id"], me["id"])))
        db.commit()
    assert (
        client.delete(endpoint + "/" + created["id"]).json()["code"]
        == "LAST_PROJECT_ADMIN"
    )
    assert (
        client.put(endpoint, json={"username": "reader", "role": "viewer"}).json()[
            "code"
        ]
        == "LAST_PROJECT_ADMIN"
    )
    events = client.get(f"{BASE}/projects/{project['id']}/audit").json()
    assert any(e["action"] == "member.remove" for e in events)


def test_live_submission_idempotency_survives_service_disconnect(
    client, demo, monkeypatch
):
    from app.routers import tasks

    _, images = demo
    body = {"image_id": images["7301"]["id"], "mode": "live_inference"}
    headers = {"Idempotency-Key": "live-reconnect-idempotent"}
    monkeypatch.setattr(tasks, "health", lambda: {"available": True, "reason": "已连接"})
    created = client.post(BASE + "/analysis-tasks", json=body, headers=headers)
    assert created.status_code == 202
    monkeypatch.setattr(
        tasks, "health", lambda: {"available": False, "reason": "GPU 服务未连接"}
    )
    again = client.post(BASE + "/analysis-tasks", json=body, headers=headers)
    assert again.status_code == 202 and again.json()["id"] == created.json()["id"]
    assert (
        client.post(
            BASE + "/analysis-tasks",
            json={**body, "strategy": "single_view"},
            headers=headers,
        ).status_code
        == 409
    )
