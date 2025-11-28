from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "XYZRank API"
    environment: str = "development"

    # 数据库类型：sqlite 或 mysql
    db_type: str = "sqlite"
    
    # MySQL配置（当db_type=mysql时使用）
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "xyzrank"
    mysql_password: str = "xyzrank"
    mysql_db: str = "xyzrank"
    mysql_echo: bool = False
    
    # SQLite配置（当db_type=sqlite时使用）
    sqlite_db_path: str = "xyzrank.db"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def database_url_async(self) -> str:
        if self.db_type == "sqlite":
            # SQLite异步连接
            db_path = Path(__file__).parent.parent.parent / self.sqlite_db_path
            return f"sqlite+aiosqlite:///{db_path}"
        else:
            # MySQL异步连接
            return (
                "mysql+asyncmy://"
                f"{quote_plus(self.mysql_user)}:{quote_plus(self.mysql_password)}"
                f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
