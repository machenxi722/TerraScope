from sqlalchemy import select
from ..config import settings
from ..errors import require
from ..models import ModelVersion, Project, ProjectMember, User
from ..security import hash_password
from .catalog import DELTA_SHA, MODEL_ID, PREPROCESS, checked_json, read_demo
from .images import ingest_image


def seed_model(db):
    if not db.get(ModelVersion, MODEL_ID):
        db.add(
            ModelVersion(
                id=MODEL_ID,
                name="TerraScope flooded roads 最终增量版本",
                delta_sha256=DELTA_SHA,
                preprocess_version=PREPROCESS,
                strategies=["single_view", "tta4"],
            )
        )
        db.flush()


def init_admin(db):
    seed_model(db)
    user = db.scalar(select(User).where(User.username == settings.admin_username))
    if not user:
        require(
            len(settings.admin_password) >= 12,
            400,
            "ADMIN_PASSWORD",
            "首次初始化必须通过环境变量设置至少 12 位管理员密码",
        )
        user = User(
            username=settings.admin_username,
            password_hash=hash_password(settings.admin_password),
            is_admin=True,
        )
        db.add(user)
        db.flush()
    return user


def seed_demo(db, user):
    manifest = settings.demo_dir / "manifest.json"
    require(manifest.is_file(), 409, "DATASET_REQUIRED", "本仓库不附带示例数据；请先安装经校验的数据集，或创建项目并上传影像")
    records = checked_json("manifest.json")["images"]
    require(bool(records), 409, "DATASET_REQUIRED", "本仓库不附带示例数据；请先安装经校验的数据集，或创建项目并上传影像")
    seed_model(db)
    project = db.scalar(
        select(Project)
        .where(
            Project.is_demo.is_(True),
            Project.created_by == user.id,
            Project.archived.is_(False),
        )
        .order_by(Project.created_at)
    )
    if not project:
        project = Project(
            name="FloodNet 洪灾道路示范项目",
            description="2026-10-16 审核案例；使用真实历史掩膜。影像无地理配准。",
            created_by=user.id,
            is_demo=True,
        )
        db.add(project)
        db.flush()
        db.add(ProjectMember(project_id=project.id, user_id=user.id, role="admin"))
    for record in records:
        ingest_image(
            db,
            project.id,
            read_demo(record["rgb_path"], record["rgb_sha256"]),
            f"FloodNet_{record['sample_id']}.jpg",
            "image/jpeg",
            attach_reference=True,
        )
    db.flush()
    return project
