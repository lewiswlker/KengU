import asyncpg
from fastapi import FastAPI
from loguru import logger
import urllib.parse
from app.core.settings.app import AppSettings
from urllib.parse import urlparse
import aiomysql

async def connect_to_db(app: FastAPI, settings: AppSettings) -> None:
    logger.info("Connecting to MySQL")

    # 解析数据库连接字符串
    url = urlparse(str(settings.database_url))
    host = url.hostname
    port = url.port or 3306
    user = url.username
    password = urllib.parse.unquote(url.password)  # 添加 URL 解码
    db = url.path.lstrip("/")

    app.state.pool = await aiomysql.create_pool(
        host=host,
        port=port,
        user=user,
        password=password,
        db=db,
        minsize=getattr(settings, "min_connection_count", 1),
        maxsize=getattr(settings, "max_connection_count", 10),
    )

    logger.info("MySQL connection established")
async def close_db_connection(app: FastAPI) -> None:
    logger.info("Closing connection to database")

    await app.state.pool.close()

    logger.info("Connection closed")
