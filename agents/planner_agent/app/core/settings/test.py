import logging

from pydantic import PostgresDsn, SecretStr

from app.core.settings.app import AppSettings
from pydantic import AnyUrl


class TestAppSettings(AppSettings):
    debug: bool = True

    title: str = "Test FastAPI example application"

    secret_key: SecretStr = SecretStr("test_secret")

    database_url: AnyUrl
    max_connection_count: int = 5
    min_connection_count: int = 5

    logging_level: int = logging.DEBUG
