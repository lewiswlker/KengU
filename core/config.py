import os

class Settings:
    # LLM
    LLM_API_KEY: str = ""
    LLM_API_ENDPOINT: str = ""
    LLM_MODEL_NAME: str = ""

    # Database (defaults can be overridden in `.env`)
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASS: str = os.getenv("DB_PASS", "123456")
    DB_HOST: str = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_NAME: str = os.getenv("DB_NAME", "kengu")
    DB_DRIVER: str = os.getenv("DB_DRIVER", "pymysql")

settings = Settings()
