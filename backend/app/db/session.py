from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


def _build_engine():
    engine_kwargs = {
        "echo": settings.mysql_echo if hasattr(settings, 'mysql_echo') else False,
    }
    
    # SQLite不需要连接池配置
    if settings.db_type == "sqlite":
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # MySQL需要连接池配置
        engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["pool_recycle"] = 1800
    
    return create_async_engine(
        settings.database_url_async,
        **engine_kwargs
    )


engine = _build_engine()
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        yield session
