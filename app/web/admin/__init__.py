from fastapi import APIRouter

from app.web.admin import athletes, auth, category_workspace, clubs, dashboard_tournaments
from app.web.admin._shared import NotAuthenticated

router = APIRouter(tags=["admin"])
router.include_router(auth.router, prefix="/admin")
router.include_router(dashboard_tournaments.router, prefix="/admin")
router.include_router(clubs.router, prefix="/admin")
router.include_router(athletes.router, prefix="/admin")
router.include_router(category_workspace.router, prefix="/admin")
