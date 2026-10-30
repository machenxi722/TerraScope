"""Run two real GPU jobs through the business API and compare native masks with sample 7301."""

import argparse
import hashlib
import io
import json
import time
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import httpx
import numpy as np
from dotenv import dotenv_values
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000/api/v1")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "docs/evidence/autodl-acceptance.json"
    )
    args = parser.parse_args()
    env = dotenv_values(ROOT / ".env")
    evidence = {
        "tested_at": datetime.now(UTC).isoformat(),
        "sample": "7301",
        "runs": [],
    }
    sample = ROOT / "data/demo/images/7301"

    with httpx.Client(base_url=args.url, timeout=30, trust_env=False) as client:

        def request(method, path, **kw):
            response = client.request(method, path, **kw)
            response.raise_for_status()
            return response

        login = request(
            "POST",
            "/auth/login",
            json={
                "username": env["TERRA_ADMIN_USERNAME"],
                "password": env["TERRA_ADMIN_PASSWORD"],
            },
        ).json()
        client.headers["X-CSRF-Token"] = login["csrf_token"]
        capabilities = request("GET", "/system/capabilities").json()["live_inference"]
        if not capabilities["available"]:
            raise SystemExit(capabilities["reason"])
        evidence["gpu"] = capabilities
        project = request(
            "POST",
            "/projects",
            json={"name": "AutoDL 实机验收 " + datetime.now().strftime("%m%d-%H%M")},
        ).json()
        image = request(
            "POST",
            f"/projects/{project['id']}/images",
            files={
                "file": ("7301.jpg", (sample / "RGB.jpg").read_bytes(), "image/jpeg")
            },
        ).json()
        evidence.update(project_id=project["id"], image_id=image["id"])
        for strategy in ["single_view", "tta4"]:
            key = "autodl-verify-" + uuid.uuid4().hex
            payload = {
                "image_id": image["id"],
                "mode": "live_inference",
                "model_version": "long_bce_lovasz",
                "strategy": strategy,
            }
            job = request(
                "POST",
                "/analysis-tasks",
                headers={"Idempotency-Key": key},
                json=payload,
            ).json()
            assert (
                request(
                    "POST",
                    "/analysis-tasks",
                    headers={"Idempotency-Key": key},
                    json=payload,
                ).json()["id"]
                == job["id"]
            )
            print(f"{strategy}: submitted {job['id']}", flush=True)
            deadline = time.monotonic() + 600
            while time.monotonic() < deadline:
                job = request("GET", "/analysis-tasks/" + job["id"]).json()
                if job["status"] in {"SUCCEEDED", "FAILED", "CANCELED"}:
                    break
                time.sleep(2)
            assert job["status"] == "SUCCEEDED", job
            prediction = request("GET", "/predictions/" + job["prediction_id"]).json()
            assert prediction["contract"]["source_mode"] == "live_inference"
            assert prediction["evaluation"] is None  # Only RGB was uploaded.
            mask_data = request(
                "GET", f"/assets/{prediction['mask_asset_id']}/download"
            ).content
            actual = np.asarray(Image.open(io.BytesIO(mask_data))) > 0
            reference = np.asarray(Image.open(sample / (strategy + ".png"))) > 0
            assert actual.shape == reference.shape == (image["height"], image["width"])
            disagreement = float(np.mean(actual != reference))
            run = {
                "strategy": strategy,
                "task_id": job["id"],
                "prediction_id": prediction["id"],
                "input_sha256": image["input_sha256"],
                "mask_sha256": hashlib.sha256(mask_data).hexdigest(),
                "width": image["width"],
                "height": image["height"],
                "disagreement_fraction": disagreement,
                "pred_pixels": int(actual.sum()),
                "metrics": prediction["metrics"],
                "runtime": prediction["contract"]["runtime"],
            }
            evidence["runs"].append(run)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(evidence, ensure_ascii=False, indent=2) + "\n"
            )
            assert disagreement <= 1e-4, f"Reference mismatch: {disagreement}"
            print(
                f"{strategy}: passed, disagreement={disagreement:.8f}, pixels={actual.sum()}",
                flush=True,
            )
        report = request(
            "POST",
            "/reports",
            headers={"Idempotency-Key": "autodl-report-" + uuid.uuid4().hex},
            json={"prediction_id": prediction["id"], "review_revision": 0},
        ).json()
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            report = request("GET", "/reports/" + report["id"]).json()
            if report["status"] in {"SUCCEEDED", "FAILED"}:
                break
            time.sleep(1)
        assert report["status"] == "SUCCEEDED", report
        data = request(
            "GET", "/assets/" + report["files"]["evidence.zip"] + "/download"
        ).content
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            assert archive.read("report.pdf").startswith(b"%PDF")
            for line in archive.read("SHA256SUMS.txt").decode().splitlines():
                checksum, name = line.split("  ")
                assert hashlib.sha256(archive.read(name)).hexdigest() == checksum
        evidence.update(report_id=report["id"], report_verified=True, passed=True)
        args.output.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2) + "\n"
        )
        print(
            "Live inference, native masks, statistics and evidence export passed.",
            flush=True,
        )


if __name__ == "__main__":
    main()
