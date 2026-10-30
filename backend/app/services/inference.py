"""Controlled asynchronous GPU boundary. Ground truth is never sent."""

import logging
import time
from urllib.parse import urlsplit

import httpx

from ..config import settings
from ..errors import DomainError, require
from .catalog import DELTA_SHA, PREPROCESS
from .storage import sha256

log = logging.getLogger(__name__)


def client(timeout=30):
    url = urlsplit(settings.model_service_url)
    safe = url.scheme == "https" and bool(url.hostname)
    if settings.model_transport == "ssh_tunnel":
        safe = url.scheme == "http" and url.hostname == "127.0.0.1" and bool(url.port)
    safe = (
        safe
        and not (url.username or url.password or url.query or url.fragment)
        and url.path in {"", "/"}
    )
    require(
        safe,
        503,
        "MODEL_UNAVAILABLE",
        "请配置 HTTPS 模型服务或本机 SSH 隧道",
    )
    return httpx.Client(
        base_url=settings.model_service_url.rstrip("/"),
        headers={"Authorization": "Bearer " + settings.model_service_token},
        timeout=timeout,
        follow_redirects=False,
        trust_env=False,
    )


def health():
    if not settings.model_service_url or not settings.model_service_token:
        return {"available": False, "reason": "尚未配置 GPU 服务与完整模型权重"}
    try:
        with client(timeout=4) as c:
            response = c.get("/health")
            response.raise_for_status()
            body = response.json()
            if body.get("ready") is not True:
                state = body.get("state", "error")
                return {
                    "available": False,
                    "state": state,
                    "reason": {
                        "loading": "模型加载中",
                        "not_configured": "模型路径待配置",
                        "error": "模型加载失败，请检查 GPU 服务日志",
                    }.get(state, "模型尚未就绪"),
                }
            require(
                body.get("ready") is True
                and body.get("delta_sha256") == DELTA_SHA
                and body.get("preprocess_version") == PREPROCESS,
                503,
                "MODEL_VERSION",
                "模型服务版本尚未通过校验",
            )
            return {
                "available": True,
                "reason": "模型服务已连接并验证版本",
                "device": body.get("device"),
                "state": "ready",
                "queue_depth": body.get("queue_depth", 0),
                "running_jobs": body.get("running_jobs", 0),
                "base_manifest_sha256": body.get("base_manifest_sha256"),
            }
    except httpx.HTTPStatusError as exc:
        return {
            "available": False,
            "state": "unauthorized" if exc.response.status_code == 401 else "offline",
            "reason": "模型服务令牌校验失败"
            if exc.response.status_code == 401
            else "GPU 服务未启动",
        }
    except (httpx.HTTPError, ValueError, DomainError):
        return {"available": False, "state": "offline", "reason": "GPU 服务未连接"}


def infer(task, image, image_bytes, checkpoint):
    started = time.monotonic()
    with client() as c:
        job_id = None

        def progress(message):
            try:
                checkpoint("INFERENCING", message)
            except Exception as exc:
                if job_id and getattr(exc, "cancel_remote", False):
                    try:
                        c.post(f"/inference-jobs/{job_id}/cancel").raise_for_status()
                    except httpx.HTTPError:
                        log.warning(
                            "Remote cancellation unavailable for GPU job %s", job_id
                        )
                raise

        # The remote service must deduplicate this key, including after network timeouts.
        payload = {
            "input_sha256": image.input_sha256,
            "width": image.width,
            "height": image.height,
            "model_version": task.config["model_version"],
            "strategy": task.config["strategy"],
            "threshold": 0,
            "preprocess_version": PREPROCESS,
            "delta_sha256": DELTA_SHA,
        }
        import json

        for attempt in range(3):
            progress("提交或核对 GPU 作业")
            try:
                response = c.post(
                    "/inference-jobs",
                    headers={"Idempotency-Key": task.id},
                    data={"config": json.dumps(payload)},
                    files={"image": ("input", image_bytes, "application/octet-stream")},
                )
                response.raise_for_status()
                job_id = response.json()["job_id"]
                require(
                    isinstance(job_id, str)
                    and 0 < len(job_id) <= 100
                    and all(ch.isalnum() or ch in "-_" for ch in job_id),
                    502,
                    "MODEL_PROTOCOL",
                    "模型服务返回了无效作业 ID",
                )
                progress("GPU 作业 ID：" + job_id)
                break
            except httpx.HTTPStatusError as exc:
                messages = {
                    401: "模型服务令牌校验失败",
                    429: "GPU 队列已满，请稍后重试",
                    503: "GPU 模型尚未就绪",
                    507: "GPU 服务器作业空间不足",
                }
                raise DomainError(
                    503,
                    "MODEL_UNAVAILABLE",
                    messages.get(exc.response.status_code, "GPU 作业提交失败"),
                ) from exc
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt == 2:
                    raise DomainError(
                        503,
                        "MODEL_TIMEOUT",
                        "GPU 服务请求超时；请核对远端幂等作业后重试",
                    )
        waiting_message = "GPU 推理中"
        while time.monotonic() - started < settings.model_timeout_seconds:
            progress(waiting_message)
            try:
                response = c.get(f"/inference-jobs/{job_id}")
            except (httpx.TimeoutException, httpx.NetworkError):
                waiting_message = "GPU 连接恢复中"
                time.sleep(2)
                continue
            if response.status_code in {502, 503, 504}:
                waiting_message = "GPU 连接恢复中"
                time.sleep(2)
                continue
            response.raise_for_status()
            state = response.json()
            require(
                state.get("status")
                in {
                    "QUEUED",
                    "RUNNING",
                    "SUCCEEDED",
                    "FAILED",
                    "CANCELED",
                    "CANCEL_REQUESTED",
                },
                502,
                "MODEL_PROTOCOL",
                "模型服务返回了无效作业状态",
            )
            if state["status"] == "QUEUED":
                waiting_message = f"GPU 排队中 · 第 {state.get('queue_position', 1)} 位"
            else:
                waiting_message = "GPU 推理中"
            if state["status"] == "SUCCEEDED":
                require(
                    all(state.get(k) == v for k, v in payload.items()),
                    422,
                    "MODEL_PROTOCOL",
                    "GPU 产物与提交配置不一致",
                )
                result = c.get(f"/inference-jobs/{job_id}/mask")
                result.raise_for_status()
                require(
                    sha256(result.content) == state.get("mask_sha256"),
                    422,
                    "MODEL_CHECKSUM",
                    "GPU 掩膜摘要不一致",
                )
                return result.content, {
                    "job_id": job_id,
                    "device": state.get("device"),
                    "elapsed_seconds": state.get("elapsed_seconds"),
                    "base_manifest_sha256": state.get("base_manifest_sha256"),
                }
            require(
                state["status"] not in {"FAILED", "CANCELED"},
                502,
                "MODEL_FAILED",
                "GPU 推理失败，请检查模型服务作业日志",
            )
            time.sleep(2)
        try:
            c.post(f"/inference-jobs/{job_id}/cancel").raise_for_status()
        except httpx.HTTPError:
            log.warning("Timed out GPU job could not be canceled: %s", job_id)
    raise DomainError(
        503, "MODEL_TIMEOUT", "GPU 推理超时，作业 ID 保留在远端，请核对后重试"
    )
