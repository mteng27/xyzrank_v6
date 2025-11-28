from fastapi import APIRouter

from app.api.podcasts import router as podcasts_router
from app.api.imports import router as imports_router
from app.api.scraper import router as scraper_router

api_router = APIRouter()
api_router.include_router(podcasts_router)
api_router.include_router(imports_router)
api_router.include_router(scraper_router)

