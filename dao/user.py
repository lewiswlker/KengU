from typing import List, Dict, Optional
from pymysql.err import ProgrammingError, IntegrityError
from .connector import DBConnector
from typing import Optional, List, Dict
from pymysql.err import ProgrammingError, IntegrityError
from .connector import DBConnector


class UserDAO:
    def __init__(self):
        self.db_connector = DBConnector()

    def find_by_id(self, user_id: int) -> Optional[Dict]:
        sql = """
            SELECT id, user_email, pwd 
            FROM users 
            WHERE id = %s 
            LIMIT 1
        """
        try:
            with self.db_connector.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (user_id,))
                    return cursor.fetchone()
        except ProgrammingError as e:
            raise RuntimeError(f"SQL execution error: {str(e)}") from e

    def find_by_email(self, user_email: str) -> Optional[Dict]:
        sql = """
            SELECT id, user_email, pwd 
            FROM users 
            WHERE user_email = %s 
            LIMIT 1
        """
        try:
            with self.db_connector.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (user_email,))
                    return cursor.fetchone()
        except ProgrammingError as e:
            raise RuntimeError(f"SQL execution error: {str(e)}") from e

    def insert_user(self, user_email: str, pwd: str = "") -> Optional[int]:
        sql = """
            INSERT INTO users (user_email, pwd) 
            VALUES (%s, %s)
        """
        try:
            with self.db_connector.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (user_email, pwd))
                    conn.commit()
                    return cursor.lastrowid
        except IntegrityError as e:
            raise RuntimeError(
                f"Duplicate user email or constraint error: {str(e)}"
            ) from e
        except ProgrammingError as e:
            raise RuntimeError(f"SQL execution error: {str(e)}") from e

    def batch_insert_users(self, user_list: List[Dict[str, str]]) -> List[int]:
        if not user_list:
            return []
        
        sql = "INSERT INTO users (user_email, pwd) VALUES (%s, %s)"
        user_ids = []
        try:
            with self.db_connector.get_connection() as conn:
                with conn.cursor() as cursor:
                    for user in user_list:
                        email = user.get("user_email", "")
                        pwd = user.get("pwd", "")
                        if not email:
                            raise ValueError("user_email is required for batch insert")
                        
                        cursor.execute(sql, (email, pwd))
                        user_ids.append(cursor.lastrowid)
                    conn.commit()
                    return user_ids
        except IntegrityError as e:
            raise RuntimeError(
                f"Duplicate user email or constraint error in batch insert: {str(e)}"
            ) from e
        except (ProgrammingError, ValueError) as e:
            raise RuntimeError(f"Batch insert error: {str(e)}") from e

    def update_pwd(self, user_id: int, new_pwd: str) -> bool:
        sql = "UPDATE users SET pwd = %s WHERE id = %s"
        try:
            with self.db_connector.get_connection() as conn:
                with conn.cursor() as cursor:
                    affected_rows = cursor.execute(sql, (new_pwd, user_id))
                    conn.commit()
                    return affected_rows > 0
        except ProgrammingError as e:
            raise RuntimeError(f"SQL execution error: {str(e)}") from e

    def get_all_users(self) -> List[Dict]:
        sql = "SELECT id, user_email, pwd FROM users ORDER BY id ASC"
        try:
            with self.db_connector.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql)
                    return cursor.fetchall()
        except ProgrammingError as e:
            raise RuntimeError(f"SQL execution error: {str(e)}") from e