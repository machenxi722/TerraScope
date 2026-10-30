from fastapi import APIRouter, Query, Request, UploadFile
from fastapi.responses import Response
from collections import Counter
from sqlalchemy import func, or_, select

from ..config import settings
from ..errors import require
from ..models import AuditEvent, ImageAsset, Project, ProjectMember, User
from ..presenters import fields, image_out, project_out
from ..schemas import ImageOut, MemberIn, ProjectIn, ProjectOut, ProjectUpdate
from ..security import DB, Actor, audit, project_access
from ..services.catalog import catalog, read_catalog
from ..services.images import ingest_image

router = APIRouter(tags=["projects"])


@router.get("/cases")
def cases(user: Actor, q: str = '', split: str = '', gps_only: bool = False,
          offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)):
    return [
        {
            "sample_id": r["sample_id"],
            "split": r["split"],
            "width": r["width"],
            "height": r["height"],
            "strategies": list(r["masks"]),
            'location': r.get('location'),
            'acquired_at': r.get('acquired_at'),
        }
        for r in filtered_cases(q, split, gps_only)[offset:offset+limit]
    ]


def filtered_cases(q='', split='', gps_only=False):
    return sorted([r for r in catalog() if q.strip() in r['sample_id']
                   and (not split or r['split'] == split)
                   and (not gps_only or r.get('location'))], key=lambda r: r['sample_id'])


@router.get('/cases/summary')
def case_summary(user: Actor, q: str = '', split: str = '', gps_only: bool = False):
    rows = filtered_cases(q, split, gps_only)
    return {'total': len(rows), 'gps_count': sum(bool(r.get('location')) for r in rows),
            'splits': dict(Counter(r['split'] for r in catalog()))}


def location_feature(identifier, location, properties):
    return {'type': 'Feature', 'id': identifier,
            'geometry': {'type': 'Point', 'coordinates': [location['longitude'], location['latitude']]},
            'properties': {**properties, **location}}


@router.get('/cases/locations')
def case_locations(user: Actor, q: str = '', split: str = ''):
    return {'type': 'FeatureCollection', 'features': [
        location_feature(r['sample_id'], r['location'], {'sample_id': r['sample_id'], 'split': r['split']})
        for r in filtered_cases(q, split, True)]}


@router.get('/cases/{sample_id}/thumbnail')
def case_thumbnail(sample_id: str, user: Actor):
    row = next((r for r in catalog() if r['sample_id'] == sample_id), None)
    require(row, 404, 'CASE_NOT_FOUND', '案例不存在')
    data = read_catalog(row, row.get('thumbnail_path', row['rgb_path']), row.get('thumbnail_sha256', row['rgb_sha256']))
    return Response(data, media_type='image/jpeg')


@router.post(
    "/projects/{project_id}/cases/{sample_id}", response_model=ImageOut, status_code=201
)
def import_case(project_id: str, sample_id: str, user: Actor, db: DB, request: Request):
    project_access(db, user, project_id, {"analyst"}, True)
    record = next((r for r in catalog() if r["sample_id"] == sample_id), None)
    require(record, 404, "CASE_NOT_FOUND", "案例不存在")
    image, _ = ingest_image(
        db,
        project_id,
        read_catalog(record, record["rgb_path"], record["rgb_sha256"]),
        f"FloodNet_{sample_id}.jpg",
        "image/jpeg",
        attach_reference=True,
    )
    audit(db, user, "image.import_case", image.id, project_id, request=request)
    db.commit()
    return image_out(image)


@router.get('/projects/{project_id}/locations')
def project_locations(project_id: str, user: Actor, db: DB):
    project_access(db, user, project_id)
    rows = [image_out(i) for i in db.scalars(select(ImageAsset).where(ImageAsset.project_id == project_id))]
    return {'type': 'FeatureCollection', 'features': [
        location_feature(r['id'], r['location'], {'image_id': r['id'], 'sample_id': r['sample_id'], 'name': r['name'], 'split': r['split']})
        for r in rows if r['location']]}


@router.get("/projects", response_model=list[ProjectOut])
def projects(
    user: Actor,
    db: DB,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    query = select(Project)
    if not user.is_admin:
        query = query.join(ProjectMember).where(ProjectMember.user_id == user.id)
    return [
        project_out(db, p, project_access(db, user, p.id)[1])
        for p in db.scalars(
            query.order_by(Project.created_at.desc(), Project.id)
            .offset(offset)
            .limit(limit)
        )
    ]


@router.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectIn, user: Actor, db: DB, request: Request):
    project = Project(**body.model_dump(), created_by=user.id)
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=user.id, role="admin"))
    audit(db, user, "project.create", project.id, project.id, request=request)
    db.commit()
    return project_out(db, project, "admin")


@router.patch("/projects/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: str, body: ProjectUpdate, user: Actor, db: DB, request: Request
):
    project, role = project_access(db, user, project_id, {"admin"})
    for k, v in body.model_dump().items():
        setattr(project, k, v)
    audit(
        db,
        user,
        "project.update",
        project_id,
        project_id,
        details=body.model_dump(),
        request=request,
    )
    db.commit()
    return project_out(db, project, role)


@router.get("/projects/{project_id}/members")
def members(project_id: str, user: Actor, db: DB):
    project_access(db, user, project_id)
    return [
        {"user_id": m.user_id, "username": u.username, "role": m.role}
        for m, u in db.execute(
            select(ProjectMember, User)
            .join(User)
            .where(ProjectMember.project_id == project_id)
            .order_by(User.username)
        )
    ]


@router.put("/projects/{project_id}/members")
def set_member(project_id: str, body: MemberIn, user: Actor, db: DB, request: Request):
    project_access(db, user, project_id, {"admin"}, True)
    db.execute(select(Project).where(Project.id == project_id).with_for_update())
    target = db.scalar(select(User).where(User.username == body.username))
    require(target, 404, "USER_NOT_FOUND", "用户不存在，请先由系统管理员创建账号")
    require(target.id != user.id, 409, "SELF_ROLE_CHANGE", "不能修改自己的项目角色")
    member = db.get(ProjectMember, (project_id, target.id))
    if member:
        if member.role == "admin" and body.role != "admin":
            require_other_admin(db, project_id)
        member.role = body.role
    else:
        db.add(ProjectMember(project_id=project_id, user_id=target.id, role=body.role))
    audit(
        db,
        user,
        "member.set",
        target.id,
        project_id,
        details={"role": body.role},
        request=request,
    )
    db.commit()
    return {"ok": True}


def require_other_admin(db, project_id):
    count = db.scalar(
        select(func.count())
        .select_from(ProjectMember)
        .where(ProjectMember.project_id == project_id, ProjectMember.role == "admin")
    )
    require(count > 1, 409, "LAST_PROJECT_ADMIN", "请先指定另一位项目管理员")


@router.delete("/projects/{project_id}/members/{user_id}", status_code=204)
def remove_member(project_id: str, user_id: str, user: Actor, db: DB, request: Request):
    project_access(db, user, project_id, {"admin"}, True)
    db.execute(select(Project).where(Project.id == project_id).with_for_update())
    require(user_id != user.id, 409, "SELF_ROLE_CHANGE", "不能移除自己的项目权限")
    member = db.get(ProjectMember, (project_id, user_id))
    require(member, 404, "MEMBER_NOT_FOUND", "项目成员不存在")
    if member.role == "admin":
        require_other_admin(db, project_id)
    db.delete(member)
    audit(db, user, "member.remove", user_id, project_id, request=request)
    db.commit()


@router.get("/projects/{project_id}/images", response_model=list[ImageOut])
def images(
    project_id: str,
    user: Actor,
    db: DB,
    q: str = "",
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    project_access(db, user, project_id)
    query = select(ImageAsset).where(ImageAsset.project_id == project_id)
    if q:
        query = query.where(
            or_(
                ImageAsset.name.icontains(q, autoescape=True),
                ImageAsset.sample_id.contains(q, autoescape=True),
            )
        )
    return [
        image_out(i)
        for i in db.scalars(
            query.order_by(ImageAsset.created_at, ImageAsset.id)
            .offset(offset)
            .limit(limit)
        )
    ]


@router.post("/projects/{project_id}/images", response_model=ImageOut, status_code=201)
async def upload(
    project_id: str, file: UploadFile, user: Actor, db: DB, request: Request
):
    project_access(db, user, project_id, {"analyst"}, True)
    data = await file.read(settings.max_upload_bytes + 1)
    image, created = ingest_image(
        db, project_id, data, file.filename or "", file.content_type
    )
    if created:
        audit(db, user, "image.upload", image.id, project_id, request=request)
    db.commit()
    return image_out(image)


@router.get("/images/{image_id}", response_model=ImageOut)
def image_detail(image_id: str, user: Actor, db: DB):
    image = db.get(ImageAsset, image_id)
    require(image, 404, "NOT_FOUND", "影像不存在")
    project_access(db, user, image.project_id)
    return image_out(image)


@router.get("/projects/{project_id}/audit")
def activities(
    project_id: str,
    user: Actor,
    db: DB,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    project_access(db, user, project_id)
    return [
        {
            **fields(e, "id action object_id details request_id created_at"),
            "actor": db.get(User, e.user_id).username,
        }
        for e in db.scalars(
            select(AuditEvent)
            .where(AuditEvent.project_id == project_id)
            .order_by(AuditEvent.created_at.desc(), AuditEvent.id)
            .offset(offset)
            .limit(limit)
        )
    ]
