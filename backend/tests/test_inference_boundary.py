import hashlib
import importlib
import io
import json
import time

from fastapi.testclient import TestClient
from PIL import Image


def test_gpu_job_protocol_without_loading_weights(monkeypatch, tmp_path):
    """Verify the HTTP/state boundary using a test-only engine; this is not a GPU benchmark."""
    monkeypatch.setenv("MODEL_JOB_DIR", str(tmp_path))
    service = importlib.import_module("model_service.server")
    monkeypatch.setattr(service, "ROOT", tmp_path)
    monkeypatch.setattr(service, "TOKEN", "test-model-token-at-least-24-characters")
    monkeypatch.delenv("MODEL_BASE_PATH", raising=False)
    monkeypatch.delenv("MODEL_DELTA_PATH", raising=False)
    monkeypatch.delenv("MODEL_BASE_MANIFEST", raising=False)

    class TestEngine:
        device = "TEST_ONLY_CPU_STUB"
        base_manifest_sha256 = "0" * 64

        def predict(self, image, strategy, cancel_check=lambda: False):
            return Image.new("L", image.size, 0)

    output = io.BytesIO()
    Image.new("RGB", (5, 4), (1, 2, 3)).save(output, format="JPEG")
    data = output.getvalue()
    config = {
        "input_sha256": hashlib.sha256(data).hexdigest(),
        "width": 5,
        "height": 4,
        "model_version": "long_bce_lovasz",
        "strategy": "tta4",
        "threshold": 0,
        "preprocess_version": "terrascope-rgb-v1",
        "delta_sha256": service.DELTA_SHA,
    }
    with TestClient(service.app) as client:
        assert client.get("/health").status_code == 401
        assert (
            client.get(
                "/health", headers={"Authorization": "Bearer invalid"}
            ).status_code
            == 401
        )
        client.headers["Authorization"] = "Bearer " + service.TOKEN
        assert client.get("/health").json()["ready"] is False
        monkeypatch.setattr(service, "engine", TestEngine())
        headers = {"Idempotency-Key": "gpu-protocol-test-job"}

        def submit(body):
            return client.post(
                "/inference-jobs",
                headers=headers,
                files={"image": ("input.jpg", data, "image/jpeg")},
                data={"config": json.dumps(body)},
            )

        assert submit({**config, "ground_truth": "forbidden"}).status_code == 422
        assert submit({**config, "input_sha256": "0" * 64}).status_code == 422
        first = submit(config)
        assert first.status_code == 202
        assert submit(config).json() == first.json()
        assert submit({**config, "strategy": "single_view"}).status_code == 409
        job = first.json()["job_id"]
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            result = client.get("/inference-jobs/" + job).json()
            if result["status"] == "SUCCEEDED":
                break
            time.sleep(0.05)
        assert result["status"] == "SUCCEEDED"
        mask = client.get(f"/inference-jobs/{job}/mask")
        assert hashlib.sha256(mask.content).hexdigest() == result["mask_sha256"]
        assert Image.open(io.BytesIO(mask.content)).size == (5, 4)


def test_remote_cancel_and_queue_limit(monkeypatch, tmp_path):
    from model_service import server as service
    from model_service.engine import InferenceCanceled

    monkeypatch.setattr(service, "ROOT", tmp_path)
    monkeypatch.setattr(service, "TOKEN", "test-model-token-at-least-24-characters")
    for key in ["MODEL_BASE_PATH", "MODEL_DELTA_PATH", "MODEL_BASE_MANIFEST"]:
        monkeypatch.delenv(key, raising=False)

    class BlockingEngine:
        device = "TEST_ONLY"
        base_manifest_sha256 = "0" * 64

        def predict(self, image, strategy, cancel_check):
            while not cancel_check():
                time.sleep(0.01)
            raise InferenceCanceled()

    output = io.BytesIO()
    Image.new("RGB", (4, 3)).save(output, "PNG")
    data = output.getvalue()
    config = {
        "input_sha256": hashlib.sha256(data).hexdigest(),
        "width": 4,
        "height": 3,
        "model_version": "long_bce_lovasz",
        "strategy": "single_view",
        "threshold": 0,
        "preprocess_version": "terrascope-rgb-v1",
        "delta_sha256": service.DELTA_SHA,
    }
    with TestClient(service.app) as client:
        client.headers["Authorization"] = "Bearer " + service.TOKEN
        monkeypatch.setattr(service, "engine", BlockingEngine())

        def submit(key):
            return client.post(
                "/inference-jobs",
                headers={"Idempotency-Key": key},
                files={"image": ("image.png", data, "image/png")},
                data={"config": json.dumps(config)},
            )

        first = submit("running-job").json()["job_id"]
        deadline = time.monotonic() + 3
        while client.get("/inference-jobs/" + first).json()["status"] != "RUNNING":
            assert time.monotonic() < deadline
            time.sleep(0.02)
        second = submit("queued-job").json()["job_id"]
        assert (
            client.post(f"/inference-jobs/{second}/cancel").json()["status"]
            == "CANCELED"
        )
        monkeypatch.setattr(service, "MAX_QUEUE", 1)
        assert submit("overflow-job").status_code == 429
        assert submit("running-job").json()["job_id"] == first
        assert client.post(f"/inference-jobs/{first}/cancel").json()["status"] in {
            "CANCEL_REQUESTED",
            "CANCELED",
        }
        while client.get("/inference-jobs/" + first).json()["status"] != "CANCELED":
            assert time.monotonic() < deadline
            time.sleep(0.02)
        assert client.get(f"/inference-jobs/{first}/mask").status_code == 409


def test_transport_is_https_or_explicit_loopback_tunnel(monkeypatch):
    import pytest
    from app.errors import DomainError
    from app.services import inference

    for mode, url, allowed in [
        ("https", "http://127.0.0.1:18100", False),
        ("https", "https://gpu.example.test", True),
        ("ssh_tunnel", "http://127.0.0.1:18100", True),
        ("ssh_tunnel", "http://gpu.example.test:8100", False),
        ("ssh_tunnel", "http://127.0.0.1.evil.test:8100", False),
        ("ssh_tunnel", "http://user:pass@127.0.0.1:8100", False),
    ]:
        monkeypatch.setattr(inference.settings, "model_transport", mode)
        monkeypatch.setattr(inference.settings, "model_service_url", url)
        if allowed:
            inference.client().close()
        else:
            with pytest.raises(DomainError):
                inference.client()


def test_backend_recovers_poll_disconnect_and_verifies_mask(monkeypatch):
    from types import SimpleNamespace

    import httpx
    from app.services import inference

    data = b"image-fixture"
    mask = b"mask-fixture"
    payload = {
        "input_sha256": hashlib.sha256(data).hexdigest(),
        "width": 4,
        "height": 3,
        "model_version": "long_bce_lovasz",
        "strategy": "tta4",
        "threshold": 0,
        "preprocess_version": inference.PREPROCESS,
        "delta_sha256": inference.DELTA_SHA,
    }
    polls = []

    def handler(request):
        if request.method == "POST":
            assert request.headers["Idempotency-Key"] == "job-test"
            assert b"ground_truth" not in request.content
            return httpx.Response(202, json={"job_id": "remote-123"})
        if request.url.path.endswith("/mask"):
            return httpx.Response(200, content=mask)
        polls.append(1)
        if len(polls) == 1:
            raise httpx.ConnectError("temporary disconnect")
        return httpx.Response(
            200,
            json={
                "status": "SUCCEEDED",
                **payload,
                "mask_sha256": hashlib.sha256(mask).hexdigest(),
                "base_manifest_sha256": "a" * 64,
            },
        )

    monkeypatch.setattr(
        inference,
        "client",
        lambda: httpx.Client(
            base_url="https://gpu.test", transport=httpx.MockTransport(handler)
        ),
    )
    monkeypatch.setattr(inference.time, "sleep", lambda _: None)
    result, runtime = inference.infer(
        SimpleNamespace(id="job-test", config=payload),
        SimpleNamespace(**payload),
        data,
        lambda *args: None,
    )
    assert result == mask and len(polls) == 2
    assert runtime["base_manifest_sha256"] == "a" * 64


def test_backend_cancel_does_not_cancel_another_workers_lease(monkeypatch):
    from types import SimpleNamespace

    import httpx
    import pytest
    from app.services import inference
    from app.services.tasks import Canceled

    for requested in (True, False):
        canceled = []

        def handler(request, canceled=canceled):
            if request.url.path.endswith("/cancel"):
                canceled.append(request.url.path)
                return httpx.Response(200, json={"status": "CANCELED"})
            return httpx.Response(202, json={"job_id": "remote-cancel-job"})

        def checkpoint(stage, message, requested=requested):
            if message.startswith("GPU 作业 ID"):
                raise Canceled(cancel_remote=requested)

        monkeypatch.setattr(
            inference,
            "client",
            lambda: httpx.Client(
                base_url="https://gpu.test", transport=httpx.MockTransport(handler)
            ),
        )
        with pytest.raises(Canceled):
            inference.infer(
                SimpleNamespace(
                    id="task-id",
                    config={"model_version": "long_bce_lovasz", "strategy": "tta4"},
                ),
                SimpleNamespace(input_sha256="a" * 64, width=4, height=3),
                b"image",
                checkpoint,
            )
        assert bool(canceled) is requested
