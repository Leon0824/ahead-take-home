from fastapi import APIRouter

from app.routers import me_router, system_router, auth_router, file_router, fcs_file_router



router = APIRouter()
router.include_router(auth_router.router)
router.include_router(me_router.router)
router.include_router(file_router.router)
router.include_router(fcs_file_router.router)
router.include_router(system_router.router)
