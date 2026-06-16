from fastapi import APIRouter

from worknexus.modules.audit.router import router as audit_router
from worknexus.modules.dashboards.router import router as dashboards_router
from worknexus.modules.home.router import router as home_router
from worknexus.modules.identity.router import router as identity_router
from worknexus.modules.intake.router import router as intake_router
from worknexus.modules.projects.router import router as projects_router
from worknexus.modules.settings.router import router as settings_router
from worknexus.modules.skills.router import router as skills_router
from worknexus.modules.system.router import router as system_router
from worknexus.modules.work_items.router import router as work_items_router
from worknexus.modules.workchat.router import router as workchat_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(system_router)
api_router.include_router(identity_router)
api_router.include_router(projects_router)
api_router.include_router(work_items_router)
api_router.include_router(intake_router)
api_router.include_router(dashboards_router)
api_router.include_router(skills_router)
api_router.include_router(workchat_router)
api_router.include_router(audit_router)
api_router.include_router(home_router)
api_router.include_router(settings_router)
