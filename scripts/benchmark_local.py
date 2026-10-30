"""A small authenticated local query sample, not a load or capacity benchmark."""

import json
import math
import time
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    values = {}
    for line in (ROOT / ".env").read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    with httpx.Client(base_url="http://127.0.0.1:5173/api/v1", timeout=20) as client:
        result = client.post(
            "/auth/login",
            json={
                "username": values["TERRA_ADMIN_USERNAME"],
                "password": values["TERRA_ADMIN_PASSWORD"],
            },
        )
        result.raise_for_status()
        samples = []
        for _ in range(40):
            start = time.perf_counter()
            response = client.get("/projects")
            response.raise_for_status()
            samples.append((time.perf_counter() - start) * 1000)
        samples.sort()
        report = {
            "scope": "40 serial authenticated GET /projects via Vite proxy; localhost; SQLite; development mode",
            "n": len(samples),
            "p50_ms": round(samples[len(samples) // 2], 2),
            "p95_ms": round(samples[math.ceil(len(samples) * 0.95) - 1], 2),
            "max_ms": round(max(samples), 2),
            "not_measured": [
                "multi-user load",
                "production PostgreSQL",
                "image switching p95",
                "GPU latency",
            ],
        }
        (ROOT / "docs/evidence/local-query-sample.json").write_text(
            json.dumps(report, indent=2)
        )
        print(json.dumps(report))


if __name__ == "__main__":
    main()
