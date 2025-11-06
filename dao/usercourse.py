"""
User Course Data Access Object module
"""

from typing import List, Dict, Optional
from pymysql.err import ProgrammingError, IntegrityError
from .connector import DBConnector


class UserCourseDAO:
    """Data Access Object for user_courses table"""

    def __init__(self):
        self.db_connector = DBConnector()

    def find_user_courses_by_userid(self, user_id: int) -> List[Dict[str, int]]:
        """
        Find all courses selected by a user
        :param user_id: Target user ID
        :return: List of dictionaries containing user_id, course_id, and record id
        """
        sql = "SELECT id, user_id, course_id FROM user_courses WHERE user_id = %s"
        try:
            with self.db_connector.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (user_id,))
                    return cursor.fetchall()
        except ProgrammingError as e:
            raise RuntimeError(f"SQL execution error: {str(e)}") from e

    def insert_user_courses(self, user_id: int, course_id: int) -> Optional[int]:
        """
        Insert user-course mapping
        :param user_id: User ID
        :param course_id: Course ID (must exist in courses table)
        :return: Auto-generated record ID if successful, None otherwise
        """
        sql = "INSERT INTO user_courses (user_id, course_id) VALUES (%s, %s)"
        try:
            with self.db_connector.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (user_id, course_id))
                    conn.commit()
                    return cursor.lastrowid
        except IntegrityError as e:
            raise RuntimeError(
                f"Foreign key constraint error (course_id not exists) or duplicate: {str(e)}"
            ) from e
        except ProgrammingError as e:
            raise RuntimeError(f"SQL execution error: {str(e)}") from e
