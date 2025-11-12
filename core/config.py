from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Pydantic v2: configure env file and ignore extra env keys
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    LLM_API_KEY: str
    LLM_API_ENDPOINT: str
    LLM_MODEL_NAME: str


settings = Settings()
