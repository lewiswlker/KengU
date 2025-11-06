from app.core.settings.app import AppSettings
from pydantic import AnyUrl, BaseSettings


class ProdAppSettings(AppSettings):
    class Config(AppSettings.Config):
        database_url: AnyUrl
        env_file = "prod.env"
