from fastapi import APIRouter

from worknexus.modules.identity.router import router as identity_router
from worknexus.modules.projects.router import router as projects_router
from worknexus.modules.system.router import router as system_router
from worknexus.modules.work_items.router import router as work_items_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(system_router)
api_router.include_router(identity_router)
api_router.include_router(projects_router)
api_router.include_router(work_items_router)
