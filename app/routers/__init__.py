from fastapi import APIRouter

from app.routers import system_router



router = APIRouter()
router.include_router(system_router.router)
