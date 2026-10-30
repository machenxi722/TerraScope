import time
import uuid
from typing import Any
from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

J = JSON().with_variant(JSONB, "postgresql")


def uid():
    return str(uuid.uuid4())


class Identity:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class User(Identity, Base):
    __tablename__ = "users"
    username: Mapped[str] = mapped_column(String(80), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    window_start: Mapped[float] = mapped_column(Float, default=time.time)


class SessionToken(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    csrf: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[float] = mapped_column(Float)


class Project(Identity, Base):
    __tablename__ = "projects"
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class ProjectMember(Base):
    __tablename__ = "project_members"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(20))


class AssetFile(Identity, Base):
    __tablename__ = "asset_files"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    path: Mapped[str] = mapped_column(Text, unique=True)
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    media_type: Mapped[str] = mapped_column(String(80))
    filename: Mapped[str] = mapped_column(String(180))


class ImageAsset(Identity, Base):
    __tablename__ = "images"
    __table_args__ = (UniqueConstraint("project_id", "input_sha256"),)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    sample_id: Mapped[str | None] = mapped_column(String(80))
    split: Mapped[str] = mapped_column(String(20), default="unassigned")
    input_sha256: Mapped[str] = mapped_column(String(64))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    original_asset_id: Mapped[str] = mapped_column(ForeignKey("asset_files.id"))
    display_asset_id: Mapped[str] = mapped_column(ForeignKey("asset_files.id"))
    thumbnail_asset_id: Mapped[str] = mapped_column(ForeignKey("asset_files.id"))
    label_asset_id: Mapped[str | None] = mapped_column(ForeignKey("asset_files.id"))
    coordinate_mode: Mapped[str] = mapped_column(String(20), default="pixel")
    acquired_at: Mapped[str | None] = mapped_column(String(40))
    transforms: Mapped[dict] = mapped_column(J, default=dict)


class ModelVersion(Base):
    __tablename__ = "model_versions"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    delta_sha256: Mapped[str] = mapped_column(String(64))
    base_sha256: Mapped[str | None] = mapped_column(String(64))
    preprocess_version: Mapped[str] = mapped_column(String(80))
    strategies: Mapped[list] = mapped_column(J)


class AnalysisTask(Identity, Base):
    __tablename__ = "analysis_tasks"
    __table_args__ = (UniqueConstraint("project_id", "idempotency_key"),)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    image_id: Mapped[str] = mapped_column(ForeignKey("images.id"))
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("analysis_tasks.id"))
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    idempotency_key: Mapped[str] = mapped_column(String(120))
    request_digest: Mapped[str] = mapped_column(String(64))
    config: Mapped[dict] = mapped_column(J)
    status: Mapped[str] = mapped_column(String(30), default="QUEUED", index=True)
    logs: Mapped[list] = mapped_column(J, default=list)
    error: Mapped[dict | None] = mapped_column(J)
    lease_token: Mapped[str | None] = mapped_column(String(36))
    lease_until: Mapped[float] = mapped_column(Float, default=0)
    finished_at: Mapped[float | None] = mapped_column(Float)


class Prediction(Identity, Base):
    __tablename__ = "predictions"
    task_id: Mapped[str] = mapped_column(ForeignKey("analysis_tasks.id"), unique=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    image_id: Mapped[str] = mapped_column(ForeignKey("images.id"), index=True)
    contract: Mapped[dict] = mapped_column(J)
    metrics: Mapped[dict] = mapped_column(J)
    evaluation: Mapped[dict | None] = mapped_column(J)
    mask_asset_id: Mapped[str] = mapped_column(ForeignKey("asset_files.id"))
    overlay_asset_id: Mapped[str] = mapped_column(ForeignKey("asset_files.id"))
    layer_asset_id: Mapped[str] = mapped_column(ForeignKey("asset_files.id"))
    difference_asset_id: Mapped[str | None] = mapped_column(
        ForeignKey("asset_files.id")
    )
    gt_layer_asset_id: Mapped[str | None] = mapped_column(ForeignKey("asset_files.id"))
    review_revision: Mapped[int] = mapped_column(Integer, default=0)


class Review(Identity, Base):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("prediction_id", "revision"),)
    prediction_id: Mapped[str] = mapped_column(ForeignKey("predictions.id"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    decision: Mapped[str] = mapped_column(String(30))
    note: Mapped[str] = mapped_column(Text)
    annotations: Mapped[list] = mapped_column(J)


class ReportSnapshot(Identity, Base):
    __tablename__ = "report_snapshots"
    __table_args__ = (UniqueConstraint("project_id", "idempotency_key"),)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    prediction_id: Mapped[str] = mapped_column(ForeignKey("predictions.id"))
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    idempotency_key: Mapped[str] = mapped_column(String(120))
    request_digest: Mapped[str] = mapped_column(String(64))
    snapshot: Mapped[dict] = mapped_column(J)
    status: Mapped[str] = mapped_column(String(20), default="QUEUED", index=True)
    files: Mapped[dict] = mapped_column(J, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
    lease_token: Mapped[str | None] = mapped_column(String(36))
    lease_until: Mapped[float] = mapped_column(Float, default=0)


class AuditEvent(Identity, Base):
    __tablename__ = "audit_events"
    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.id"), index=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80))
    object_id: Mapped[str] = mapped_column(String(80))
    details: Mapped[dict[str, Any]] = mapped_column(J, default=dict)
    request_id: Mapped[str] = mapped_column(String(64), default="system")
