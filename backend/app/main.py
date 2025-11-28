from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import api_router
from app.core.config import settings
from app.db.session import get_db_session

# 定时任务（可选）
try:
    from app.tasks.scheduler import start_scheduler, shutdown_scheduler
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False
    def start_scheduler():
        pass
    def shutdown_scheduler():
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    if SCHEDULER_AVAILABLE:
        start_scheduler()
    yield
    # 关闭时
    if SCHEDULER_AVAILABLE:
        shutdown_scheduler()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan
)

# 添加CORS中间件（允许前端访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(api_router)


@app.get("/health", summary="Database health check")
async def health_check(session: AsyncSession = Depends(get_db_session)):
    await session.execute(text("SELECT 1"))
    return {"status": "ok", "environment": settings.environment}


@app.get("/", summary="Service metadata")
async def root():
    return {"app": settings.app_name, "environment": settings.environment}
