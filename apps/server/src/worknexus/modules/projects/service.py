from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.deps import Actor
from worknexus.modules.projects.models import Project


async def create_project(
    db: AsyncSession,
    actor: Actor,
    *,
    tenant_id: str,
    name: str,
    key: str,
    description: str | None = None,
    owner_id: str | None = None,
) -> Project:
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
