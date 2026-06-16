from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.access import Subject
from worknexus.core.deps import Actor
from worknexus.core.errors import BizError, ErrorCode
from worknexus.core.pagination import PageParams
from worknexus.modules.audit import service as audit
from worknexus.modules.audit.service import AuditAction
from worknexus.modules.identity.models import ProjectMember, User
from worknexus.modules.projects.models import Project
from worknexus.modules.projects.schemas import (
    ProjectCreateIn,
    ProjectOut,
    ProjectStatus,
    ProjectUpdateIn,
    UserBriefOut,
)


async def insert_project(
    db: AsyncSession,
    actor: Actor,
    *,
    tenant_id: str,
    name: str,
    key: str,
    description: str | None = None,
    owner_id: str | None = None,
) -> Project:
    """Building block: insert a project row (no audit, no commit).

    Composed inside larger transactions (setup seeds a project this way). The
    orchestrating caller owns audit + commit."""
    project = Project(
        tenant_id=tenant_id,
        name=name,
        key=key,
        description=description,
        owner_id=owner_id,
        settings={},
        created_by=actor.id,
        updated_by=actor.id,
    )
    db.add(project)
    await db.flush()
    return project


async def get_project(db: AsyncSession, project_id: str, tenant_id: str) -> Project:
    project = await db.get(Project, project_id)
    if project is None or project.tenant_id != tenant_id:
        raise BizError(ErrorCode.PROJECT_NOT_FOUND, "project not found")
    return project


def accessible_project_ids(subject: Subject) -> set[str] | None:
    """The project ids a subject may read. None means "all projects in the tenant"
    (owner/admin tenant roles); otherwise the explicit project-membership set.

    Mirrors identity.service.build_current_user_context so /projects, /me and /home agree."""
    if subject.tenant_roles:
        return None
    return set(subject.project_roles.keys())


async def _build_project_outs(db: AsyncSession, projects: list[Project]) -> list[ProjectOut]:
    if not projects:
        return []
    owner_ids = {p.owner_id for p in projects if p.owner_id}
    owners: dict[str, User] = {}
    if owner_ids:
        rows = (await db.execute(select(User).where(User.id.in_(owner_ids)))).scalars().all()
        owners = {u.id: u for u in rows}
    count_rows = (
        await db.execute(
            select(ProjectMember.project_id, func.count())
            .where(ProjectMember.project_id.in_([p.id for p in projects]))
            .group_by(ProjectMember.project_id)
        )
    ).all()
    counts: dict[str, int] = dict(count_rows)  # type: ignore[arg-type]  # SQLAlchemy Row → (project_id, count)
    return [
        ProjectOut(
            id=p.id,
            name=p.name,
            key=p.key,
            description=p.description,
            status=ProjectStatus(p.status),
            owner_id=p.owner_id,
            owner=UserBriefOut.model_validate(owners[p.owner_id]) if p.owner_id in owners else None,
            member_count=counts.get(p.id, 0),
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in projects
    ]


async def list_projects(
    db: AsyncSession, subject: Subject, *, status: ProjectStatus, params: PageParams
) -> tuple[list[ProjectOut], int]:
    base = select(Project).where(Project.tenant_id == subject.actor.tenant_id, Project.status == status)
    ids = accessible_project_ids(subject)
    if ids is not None:
        if not ids:
            return [], 0
        base = base.where(Project.id.in_(ids))
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    projects = (
        (await db.execute(base.order_by(Project.created_at.desc()).offset(params.offset).limit(params.page_size)))
        .scalars()
        .all()
    )
    return await _build_project_outs(db, list(projects)), total


async def get_project_detail(db: AsyncSession, actor: Actor, project_id: str) -> ProjectOut:
    project = await get_project(db, project_id, actor.tenant_id)
    return (await _build_project_outs(db, [project]))[0]


async def create_project(db: AsyncSession, actor: Actor, data: ProjectCreateIn) -> ProjectOut:
    existing = (
        await db.execute(select(Project.id).where(Project.tenant_id == actor.tenant_id, Project.key == data.key))
    ).first()
    if existing is not None:
        raise BizError(ErrorCode.PROJECT_KEY_EXISTS, "a project with this key already exists")
    project = await insert_project(
        db,
        actor,
        tenant_id=actor.tenant_id,
        name=data.name,
        key=data.key,
        description=data.description,
        owner_id=actor.id,
    )
    await audit.record(
        db,
        actor,
        action=AuditAction.PROJECT_CREATE,
        resource_type="project",
        resource_id=project.id,
        project_id=project.id,
        after={"name": data.name, "key": data.key},
    )
    await db.commit()
    return (await _build_project_outs(db, [project]))[0]


async def update_project(db: AsyncSession, actor: Actor, project_id: str, data: ProjectUpdateIn) -> ProjectOut:
    project = await get_project(db, project_id, actor.tenant_id)
    before = {"name": project.name, "description": project.description}
    fields = data.model_fields_set
    if "name" in fields and data.name is not None:
        project.name = data.name
    if "description" in fields:
        project.description = data.description
    project.updated_by = actor.id
    await db.flush()
    await audit.record(
        db,
        actor,
        action=AuditAction.PROJECT_UPDATE,
        resource_type="project",
        resource_id=project.id,
        project_id=project.id,
        before=before,
        after={"name": project.name, "description": project.description},
    )
    await db.commit()
    return (await _build_project_outs(db, [project]))[0]


async def archive_project(db: AsyncSession, actor: Actor, project_id: str) -> ProjectOut:
    project = await get_project(db, project_id, actor.tenant_id)
    if project.status != ProjectStatus.ARCHIVED:
        project.status = ProjectStatus.ARCHIVED
        project.updated_by = actor.id
        await db.flush()
        await audit.record(
            db,
            actor,
            action=AuditAction.PROJECT_ARCHIVE,
            resource_type="project",
            resource_id=project.id,
            project_id=project.id,
            before={"status": ProjectStatus.ACTIVE},
            after={"status": ProjectStatus.ARCHIVED},
        )
        await db.commit()
    return (await _build_project_outs(db, [project]))[0]
