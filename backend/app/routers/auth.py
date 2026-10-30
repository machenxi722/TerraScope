import secrets
import time
from fastapi import APIRouter, Request, Response
from sqlalchemy import select, update, delete
from ..config import settings
from ..errors import require
from ..models import LoginAttempt, SessionToken, User
from ..schemas import LoginIn, LoginOut, UserIn, UserOut
from ..security import Actor, DB, audit, digest, hash_password, verify_password

router = APIRouter(tags=["auth"])
DUMMY_HASH = hash_password(secrets.token_urlsafe(30))


@router.post("/auth/login", response_model=LoginOut)
def login(body: LoginIn, request: Request, response: Response, db: DB):
    origin = request.headers.get("origin")
    require(
        not origin or origin == str(request.base_url).rstrip("/"),
        403,
        "ORIGIN_INVALID",
        "请从同源页面登录",
    )
    key = digest(body.username.lower())
    attempt = db.get(LoginAttempt, key)
    if not attempt:
        attempt = LoginAttempt(key=key, count=0, window_start=time.time())
        db.add(attempt)
    if time.time() - attempt.window_start > 300:
        attempt.count = 0
        attempt.window_start = time.time()
    db.flush()
    allowed = db.execute(
        update(LoginAttempt)
        .where(LoginAttempt.key == key, LoginAttempt.count < 10)
        .values(count=LoginAttempt.count + 1)
    )
    db.commit()
    require(allowed.rowcount, 429, "LOGIN_RATE_LIMIT", "登录尝试过多，请五分钟后重试")
    user = db.scalar(select(User).where(User.username == body.username))
    valid = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not user.active or not valid:
        require(False, 401, "LOGIN_FAILED", "用户名或密码错误")
    db.execute(update(LoginAttempt).where(LoginAttempt.key == key).values(count=0))
    db.execute(delete(SessionToken).where(SessionToken.expires_at <= time.time()))
    token, csrf = secrets.token_urlsafe(48), secrets.token_hex(32)
    db.add(
        SessionToken(
            token_hash=digest(token),
            user_id=user.id,
            csrf=csrf,
            expires_at=time.time() + settings.session_hours * 3600,
        )
    )
    audit(db, user, "auth.login", user.id, request=request)
    db.commit()
    response.set_cookie(
        "terra_session",
        token,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="strict",
        max_age=settings.session_hours * 3600,
        path="/",
    )
    return {
        "user": {"id": user.id, "username": user.username, "is_admin": user.is_admin},
        "csrf_token": csrf,
    }


@router.get("/auth/me", response_model=LoginOut)
def me(request: Request, user: Actor):
    return {
        "user": {"id": user.id, "username": user.username, "is_admin": user.is_admin},
        "csrf_token": request.state.session.csrf,
    }


@router.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response, user: Actor, db: DB):
    db.delete(request.state.session)
    db.commit()
    response.delete_cookie("terra_session", path="/")


@router.get("/users", response_model=list[UserOut])
def users(user: Actor, db: DB):
    require(user.is_admin, 403, "ROLE_FORBIDDEN", "仅系统管理员可以查看用户列表")
    return [
        {"id": u.id, "username": u.username, "is_admin": u.is_admin}
        for u in db.scalars(select(User).order_by(User.username))
    ]


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(body: UserIn, user: Actor, db: DB, request: Request):
    require(user.is_admin, 403, "ROLE_FORBIDDEN", "仅系统管理员可以创建用户")
    require(
        not db.scalar(select(User).where(User.username == body.username)),
        409,
        "USERNAME_EXISTS",
        "用户名已存在",
    )
    result = User(username=body.username, password_hash=hash_password(body.password))
    db.add(result)
    db.flush()
    audit(db, user, "user.create", result.id, request=request)
    db.commit()
    return {"id": result.id, "username": result.username, "is_admin": result.is_admin}
