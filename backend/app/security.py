import hashlib
import hmac
import secrets
import time
from typing import Annotated
from fastapi import Depends, Request
from sqlalchemy.orm import Session
from .db import get_db
from .models import Project, ProjectMember, SessionToken, User, AuditEvent
from .errors import require

DB = Annotated[Session, Depends(get_db)]


def hash_password(password):
    salt = secrets.token_hex(16)
    return (
        salt
        + ":"
        + hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    )


def verify_password(password, stored):
    salt, expected = stored.split(":")
    actual = hashlib.scrypt(
        password.encode(), salt=salt.encode(), n=16384, r=8, p=1
    ).hex()
    return hmac.compare_digest(expected, actual)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def current_user(request: Request, db: DB):
    token = request.cookies.get("terra_session", "")
    session = db.get(SessionToken, digest(token)) if token else None
    require(
        session and session.expires_at > time.time(), 401, "AUTH_REQUIRED", "请先登录"
    )
    user = db.get(User, session.user_id)
    require(user and user.active, 401, "AUTH_REQUIRED", "账号已停用")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        require(
            hmac.compare_digest(request.headers.get("X-CSRF-Token", ""), session.csrf),
            403,
            "CSRF_INVALID",
            "会话校验失败，请刷新页面",
        )
    request.state.user_id = user.id
    request.state.session = session
    return user


Actor = Annotated[User, Depends(current_user)]


def project_access(db, user, project_id, roles=None, writable=False):
    project = db.get(Project, project_id)
    require(project, 404, "NOT_FOUND", "项目不存在")
    member = db.get(ProjectMember, (project_id, user.id))
    require(user.is_admin or member, 403, "PROJECT_FORBIDDEN", "没有该项目的访问权限")
    role = "admin" if user.is_admin else member.role
    require(
        not roles or role == "admin" or role in roles,
        403,
        "ROLE_FORBIDDEN",
        "当前角色不能执行此操作",
    )
    require(
        not writable or not project.archived,
        409,
        "PROJECT_ARCHIVED",
        "项目已归档，请先恢复",
    )
    return project, role


def audit(db, user, action, object_id, project_id=None, details=None, request=None):
    db.add(
        AuditEvent(
            user_id=user.id,
            action=action,
            object_id=object_id,
            project_id=project_id,
            details=details or {},
            request_id=getattr(request.state, "request_id", "system")
            if request
            else "system",
        )
    )
