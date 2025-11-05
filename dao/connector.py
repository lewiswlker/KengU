"""
Database connector module
"""

import pymysql
from pymysql.err import OperationalError
from typing import Optional
from contextlib import contextmanager
from .config import DatabaseConfig


class DBConnector:
    """Singleton database connection manager"""

    _instance: Optional["DBConnector"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @contextmanager
    def get_connection(self):
        """
        Provide a database connection with context manager (auto-close after use)
        :return: Database connection object
        """
        conn: Optional[pymysql.connections.Connection] = None
        try:
            conn = pymysql.connect(
                host=DatabaseConfig.HOST,
                port=DatabaseConfig.PORT,
                user=DatabaseConfig.USER,
                password=DatabaseConfig.PASSWORD,
                database=DatabaseConfig.DATABASE,
                charset=DatabaseConfig.CHARSET,
                cursorclass=pymysql.cursors.DictCursor,
            )
            yield conn
        except OperationalError as e:
            raise RuntimeError(f"Database connection failed: {str(e)}") from e
        finally:
            if conn and conn.open:
                conn.close()
