"""Single-GPU durable asynchronous API. Deploy one process behind HTTPS."""

import hashlib
import hmac
import io
import json
import logging
import os
import shutil
import sqlite3
import threading
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, ImageOps
from pydantic import BaseModel, ConfigDict, Field

from .engine import DELTA_SHA, InferenceCanceled, TerraScopeEngine

ROOT = Path(os.environ.get("MODEL_JOB_DIR", "model-runtime")).resolve()
ROOT.mkdir(parents=True, exist_ok=True)
TOKEN = os.environ.get("MODEL_API_TOKEN", "")
engine = None
stop = threading.Event()
logger = logging.getLogger(__name__)
readiness = "not_configured"
MAX_QUEUE = int(os.environ.get("MODEL_MAX_QUEUE", "8"))


def db():
    connection = sqlite3.connect(ROOT / "jobs.sqlite", timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    return connection


def auth(authorization: Annotated[str | None, Header()] = None):
    if len(TOKEN) < 24 or not hmac.compare_digest(
        authorization or "", "Bearer " + TOKEN
    ):
        raise HTTPException(401, "Invalid model service token")


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid")
    input_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    width: int = Field(gt=0, le=25000000)
    height: int = Field(gt=0, le=25000000)
    model_version: Literal["long_bce_lovasz"]
    strategy: Literal["single_view", "tta4"]
    threshold: Literal[0]
    preprocess_version: Literal["terrascope-rgb-v1"]
    delta_sha256: Literal[DELTA_SHA]


def worker(paths):
    global engine, readiness
    if all(paths):
        readiness = "loading"
        try:
            engine = TerraScopeEngine(*paths)
            readiness = "ready"
        except Exception:
            readiness = "error"
            logger.exception("Model readiness validation failed")
    while not stop.wait(0.5):
        if engine is None:
            continue
        with db() as conn:
            job = conn.execute(
                "SELECT * FROM jobs WHERE status='QUEUED' ORDER BY created_at LIMIT 1"
            ).fetchone()
            if not job:
                continue
            claimed = conn.execute(
                "UPDATE jobs SET status='RUNNING' WHERE id=? AND status='QUEUED'",
                (job["id"],),
            )
            if not claimed.rowcount:
                continue
        try:
            config = json.loads(job["config"])
            start = time.monotonic()
            with Image.open(ROOT / (job["id"] + ".input")) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")

            def canceled(job_id=job["id"]):
                with db() as conn:
                    state = conn.execute(
                        "SELECT status FROM jobs WHERE id=?", (job_id,)
                    ).fetchone()
                return stop.is_set() or state["status"] == "CANCEL_REQUESTED"

            mask = engine.predict(image, config["strategy"], cancel_check=canceled)
            target = ROOT / (job["id"] + ".png")
            temp = target.with_suffix(".tmp")
            mask.save(temp, format="PNG")
            temp.replace(target)
            result = {
                **config,
                "mask_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                "device": engine.device,
                "base_manifest_sha256": engine.base_manifest_sha256,
                "elapsed_seconds": time.monotonic() - start,
            }
            with db() as conn:
                published = conn.execute(
                    "UPDATE jobs SET status='SUCCEEDED',result=? WHERE id=? AND status='RUNNING'",
                    (json.dumps(result), job["id"]),
                )
                if not published.rowcount:
                    conn.execute(
                        "UPDATE jobs SET status='CANCELED' WHERE id=?", (job["id"],)
                    )
        except InferenceCanceled:
            with db() as conn:
                conn.execute(
                    "UPDATE jobs SET status='CANCELED' WHERE id=?", (job["id"],)
                )
        except Exception:
            logger.exception("GPU job failed: %s", job["id"])
            with db() as conn:
                conn.execute(
                    "UPDATE jobs SET status='FAILED',result=? WHERE id=?",
                    (json.dumps({"error_code": "INFERENCE_FAILED"}), job["id"]),
                )


@asynccontextmanager
async def lifespan(app):
    global engine, readiness
    engine = None
    readiness = "not_configured"
    if len(TOKEN) < 24:
        raise RuntimeError("MODEL_API_TOKEN must contain at least 24 characters")
    with db() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,key TEXT UNIQUE,digest TEXT,config TEXT,status TEXT,result TEXT,created_at REAL)"
        )
        conn.execute("UPDATE jobs SET status='QUEUED' WHERE status='RUNNING'")
        conn.execute(
            "UPDATE jobs SET status='CANCELED' WHERE status='CANCEL_REQUESTED'"
        )
    paths = [
        os.environ.get(key, "")
        for key in ["MODEL_BASE_PATH", "MODEL_DELTA_PATH", "MODEL_BASE_MANIFEST"]
    ]
    stop.clear()
    thread = threading.Thread(target=worker, args=(paths,), daemon=True)
    thread.start()
    yield
    stop.set()
    thread.join(timeout=5)


app = FastAPI(
    title="TerraScope isolated GPU service",
    lifespan=lifespan,
    dependencies=[Depends(auth)],
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.get("/health")
def health():
    with db() as conn:
        counts = dict(
            conn.execute("SELECT status,count(*) FROM jobs GROUP BY status").fetchall()
        )
    return {
        "ready": engine is not None,
        "state": "ready" if engine else readiness,
        "protocol_version": 1,
        "delta_sha256": DELTA_SHA,
        "preprocess_version": "terrascope-rgb-v1",
        "device": engine.device if engine else None,
        "base_manifest_sha256": engine.base_manifest_sha256 if engine else None,
        "queue_depth": counts.get("QUEUED", 0),
        "running_jobs": counts.get("RUNNING", 0) + counts.get("CANCEL_REQUESTED", 0),
    }


@app.post("/inference-jobs", status_code=202)
async def create_job(
    image: UploadFile,
    config: Annotated[str, Form()],
    key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=120)],
):
    if engine is None:
        raise HTTPException(503, "Model is not ready")
    try:
        parsed = Config.model_validate_json(config)
    except ValueError:
        raise HTTPException(422, "Invalid immutable inference configuration")
    data = await image.read(20 * 1024 * 1024 + 1)
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(413, "Image exceeds size limit")
    if hashlib.sha256(data).hexdigest() != parsed.input_sha256:
        raise HTTPException(422, "Input checksum mismatch")
    try:
        with Image.open(io.BytesIO(data)) as raw:
            if (
                raw.format not in {"JPEG", "PNG"}
                or raw.width * raw.height > 25_000_000
                or getattr(raw, "n_frames", 1) != 1
            ):
                raise ValueError()
            normalized = ImageOps.exif_transpose(raw)
            if normalized.size != (parsed.width, parsed.height):
                raise ValueError()
    except (OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(422, "Invalid image grid")
    frozen = parsed.model_dump_json()
    digest = hashlib.sha256(frozen.encode()).hexdigest()
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute(
            "SELECT id,digest FROM jobs WHERE key=?", (key,)
        ).fetchone()
        if existing:
            if existing["digest"] != digest:
                raise HTTPException(409, "Idempotency conflict")
            return {"job_id": existing["id"]}
        count = conn.execute(
            "SELECT count(*) FROM jobs WHERE status IN ('QUEUED','RUNNING','CANCEL_REQUESTED')"
        ).fetchone()[0]
        if count >= MAX_QUEUE:
            raise HTTPException(429, "GPU queue is full", headers={"Retry-After": "5"})
        if shutil.disk_usage(ROOT).free < 256 * 1024 * 1024:
            raise HTTPException(507, "Insufficient job storage")
        job_id = str(uuid.uuid4())
        (ROOT / (job_id + ".input")).write_bytes(data)
        conn.execute(
            "INSERT INTO jobs VALUES(?,?,?,?,?,?,?)",
            (job_id, key, digest, frozen, "QUEUED", None, time.time()),
        )
    return {"job_id": job_id}


def get_job(job_id):
    with db() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Job not found")
    return row


@app.get("/inference-jobs/{job_id}")
def status(job_id: str):
    job = get_job(job_id)
    with db() as conn:
        ahead = conn.execute(
            "SELECT count(*) FROM jobs WHERE status IN ('QUEUED','RUNNING') AND created_at<?",
            (job["created_at"],),
        ).fetchone()[0]
    return {
        "job_id": job_id,
        "status": job["status"],
        "queue_position": ahead + 1 if job["status"] == "QUEUED" else 0,
        **json.loads(job["result"] or "{}"),
    }


@app.post("/inference-jobs/{job_id}/cancel")
def cancel(job_id: str):
    get_job(job_id)
    with db() as conn:
        conn.execute(
            "UPDATE jobs SET status=CASE WHEN status='QUEUED' THEN 'CANCELED' ELSE 'CANCEL_REQUESTED' END WHERE id=? AND status IN ('QUEUED','RUNNING')",
            (job_id,),
        )
    return status(job_id)


@app.get("/inference-jobs/{job_id}/mask")
def mask(job_id: str):
    job = get_job(job_id)
    if job["status"] != "SUCCEEDED":
        raise HTTPException(409, "Job is not completed")
    return FileResponse(ROOT / (job["id"] + ".png"), media_type="image/png")
