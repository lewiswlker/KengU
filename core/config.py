from typing import Any, TYPE_CHECKING
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine  # type: ignore

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    LLM_API_KEY: str = ""
    LLM_API_ENDPOINT: str = ""
    LLM_MODEL_NAME: str = ""

    # Database (defaults can be overridden in `.env`)
    DB_USER: str = "root"
    DB_PASS: str = "123456"
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_NAME: str = "kengu"
    DB_DRIVER: str = "pymysql"

    def db_dsn(self) -> str:
        return f"mysql+{self.DB_DRIVER}://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    def create_db_engine(self, **kwargs: Any) -> "Engine":
        # import here to avoid requiring SQLAlchemy at module import time
        from sqlalchemy import create_engine  # local import
        return create_engine(self.db_dsn(), pool_pre_ping=True, **kwargs)


settings = Settings()
try:
    db_engine = settings.create_db_engine()
except Exception:
    # If SQLAlchemy is not installed or connection fails, keep None so imports don't crash
    db_engine = None
