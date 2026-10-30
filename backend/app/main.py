import logging
import time
import uuid
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.exceptions import HTTPException
from . import __version__
from .config import settings
from .errors import DomainError
from .routers import auth, projects, results, system, tasks

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger("terrascope.requests")
app = FastAPI(
    title="TerraScope 洪灾道路智能解译与调查平台",
    version=__version__,
    description="P0 API；所有业务资产访问执行项目级权限检查。",
    docs_url=None,
    redoc_url=None,
    openapi_url="/api/v1/openapi.json",
)
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts.split(",")
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request.state.request_id = uuid.uuid4().hex
    started = time.monotonic()
    length = request.headers.get("content-length", "")
    if length.isdigit() and int(length) > settings.max_upload_bytes + 1024 * 1024:
        response = JSONResponse(
            status_code=413,
            content={
                "code": "UPLOAD_TOO_LARGE",
                "message": "请求体超过上传限制",
                "field_errors": [],
                "request_id": request.state.request_id,
            },
        )
    else:
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Unhandled error request_id=%s", request.state.request_id)
            response = JSONResponse(
                status_code=500,
                content={
                    "code": "INTERNAL_ERROR",
                    "message": "服务暂时无法完成请求，请凭请求 ID 检查日志",
                    "request_id": request.state.request_id,
                    "field_errors": [],
                },
            )
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    logger.info(
        "request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
        request.state.request_id,
        request.method,
        request.url.path,
        response.status_code,
        1000 * (time.monotonic() - started),
    )
    return response


@app.exception_handler(DomainError)
async def domain_error(request, exc):
    return JSONResponse(
        status_code=exc.status,
        content={
            "code": exc.code,
            "message": exc.message,
            "field_errors": exc.field_errors,
            "request_id": request.state.request_id,
        },
    )


@app.exception_handler(RequestValidationError)
async def invalid_request(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "请求字段校验失败",
            "request_id": request.state.request_id,
            "field_errors": [
                {"field": ".".join(map(str, e["loc"])), "message": e["msg"]}
                for e in exc.errors()
            ],
        },
    )


@app.exception_handler(IntegrityError)
async def conflict(request, exc):
    return JSONResponse(
        status_code=409,
        content={
            "code": "CONCURRENT_CONFLICT",
            "message": "记录已存在或发生并发更新，请刷新后重试",
            "request_id": request.state.request_id,
            "field_errors": [],
        },
    )


@app.exception_handler(HTTPException)
async def http_error(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": "HTTP_ERROR",
            "message": str(exc.detail),
            "request_id": request.state.request_id,
            "field_errors": [],
        },
    )


for router in [
    auth.router,
    projects.router,
    tasks.router,
    results.router,
    system.router,
]:
    app.include_router(router, prefix="/api/v1")
