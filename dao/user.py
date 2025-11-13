from typing import List, Dict, Optional
from pymysql.err import ProgrammingError, IntegrityError
from .connector import DBConnector

"""
User Data Access Object module
"""
from typing import Optional, List, Dict
from pymysql.err import ProgrammingError, IntegrityError
from .connector import DBConnector


class UserDAO:
    """Data Access Object for users table (matches the structure in the image)"""
    def __init__(self):
        self.db_connector = DBConnector()

    def find_by_id(self, user_id: int) -> Optional[Dict]:
        """
        Find user info by user ID (matches users table structure: id, user_email, pwd)
        :param user_id: Target user ID
        :return: Dict of user info if exists, None otherwise
                 Keys: "id" (int), "user_email" (str), "pwd" (str)
        """
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
        """
        Find user info by user email (for email-based queries, e.g., HKU portal email check)
        :param user_email: Target user email (e.g., u3665467@connect.hku.hk)
        :return: Dict of user info if exists, None otherwise
                 Keys: "id" (int), "user_email" (str), "pwd" (str)
        """
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
        """
        Insert new user (auto-generate user ID, matches image's users table structure)
        :param user_email: Unique user email (required, e.g., HKU portal email)
        :param pwd: Password field (optional, empty by default as per image)
        :return: Auto-generated user ID if successful, None otherwise
        :raises RuntimeError: If email is duplicate or SQL execution fails
        """
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
        """
        Batch insert multiple users (for bulk operations, e.g., importing HKU user emails)
        :param user_list: List of user dicts, each with "user_email" (required) and "pwd" (optional)
                          Example: [{"user_email": "u3665467@connect.hku.hk"}, {"user_email": "uxxxxxx@connect.hku.hk"}]
        :return: List of auto-generated user IDs in the same order as input
        """
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
        """
        Update user's password (matches image's "pwd" field, for password modification)
        :param user_id: Target user ID (unique identifier)
        :param new_pwd: New password to set
        :return: True if update successful (1 row affected), False otherwise
        """
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
        """
        Get all users (for admin operations, e.g., viewing all HKU user emails)
        :return: List of user dicts, each with "id", "user_email", "pwd"
        """
        sql = "SELECT id, user_email, pwd FROM users ORDER BY id ASC"
        try:
            with self.db_connector.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql)
                    return cursor.fetchall()
        except ProgrammingError as e:
            raise RuntimeError(f"SQL execution error: {str(e)}") from e