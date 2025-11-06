"""
Course Data Access Object module
"""

from datetime import datetime
from typing import List, Tuple, Optional
from pymysql.err import ProgrammingError, IntegrityError
from .connector import DBConnector


class CourseDAO:
    """Data Access Object for courses table"""

    def __init__(self):
        self.db_connector = DBConnector()

    def find_update_time_byname(
        self, course_name: str
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Find update times by course name
        :param course_name: Target course name
        :return: Tuple of (update_time_moodle, update_time_exambase)
        """
        sql = """
            SELECT update_time_moodle, update_time_exambase 
            FROM courses 
            WHERE course_name = %s
            LIMIT 1
        """
        try:
            with self.db_connector.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (course_name,))
                    result = cursor.fetchone()
                    if result:
                        return (
                            result["update_time_moodle"],
                            result["update_time_exambase"],
                        )
                    return None, None
        except ProgrammingError as e:
            raise RuntimeError(f"SQL execution error: {str(e)}") from e

    def find_update_time_byid(
        self, course_id: int
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Find update times by course ID
        :param course_id: Target course ID
        :return: Tuple of (update_time_moodle, update_time_exambase)
        """
        sql = """
            SELECT update_time_moodle, update_time_exambase 
            FROM courses 
            WHERE id = %s
            LIMIT 1
        """
        try:
            with self.db_connector.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (course_id,))
                    result = cursor.fetchone()
                    if result:
                        return (
                            result["update_time_moodle"],
                            result["update_time_exambase"],
                        )
                    return None, None
        except ProgrammingError as e:
            raise RuntimeError(f"SQL execution error: {str(e)}") from e

    def find_id_by_name(self, course_name: str) -> Optional[int]:
        """
        Find course ID by course name
        :param course_name: Target course name
        :return: Course ID if exists, None otherwise
        """
        sql = "SELECT id FROM courses WHERE course_name = %s LIMIT 1"
        try:
            with self.db_connector.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (course_name,))
                    result = cursor.fetchone()
                    return result["id"] if result else None
        except ProgrammingError as e:
            raise RuntimeError(f"SQL execution error: {str(e)}") from e

    def find_name_by_id(self, course_id: int) -> Optional[str]:
        """
        Find course name by course ID
        :param course_id: Target course ID
        :return: Course name if exists, None otherwise
        """
        sql = "SELECT course_name FROM courses WHERE id = %s LIMIT 1"
        try:
            with self.db_connector.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (course_id,))
                    result = cursor.fetchone()
                    return result["course_name"] if result else None
        except ProgrammingError as e:
            raise RuntimeError(f"SQL execution error: {str(e)}") from e

    def insert_name(self, course_name: str) -> Optional[int]:
        """
        Insert new course name and return auto-generated ID
        :param course_name: Course name to insert (unique)
        :return: Auto-generated course ID if successful, None otherwise
        """
        sql = "INSERT INTO courses (course_name) VALUES (%s)"
        try:
            with self.db_connector.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (course_name,))
                    conn.commit()
                    return cursor.lastrowid
        except IntegrityError as e:
            raise RuntimeError(
                f"Duplicate course name or constraint error: {str(e)}"
            ) from e
        except ProgrammingError as e:
            raise RuntimeError(f"SQL execution error: {str(e)}") from e

    def insert_names(self, course_names: List[str]) -> List[int]:
        """
        Batch insert multiple course names and return auto-generated IDs
        :param course_names: List of course names to insert (each must be unique)
        :return: List of auto-generated course IDs in the same order
        """
        if not course_names:
            return []

        sql = "INSERT INTO courses (course_name) VALUES (%s)"
        course_ids = []

        try:
            with self.db_connector.get_connection() as conn:
                with conn.cursor() as cursor:
                    for course_name in course_names:
                        cursor.execute(sql, (course_name,))
                        course_ids.append(cursor.lastrowid)
                    conn.commit()
                    return course_ids
        except IntegrityError as e:
            raise RuntimeError(
                f"Duplicate course name or constraint error: {str(e)}"
            ) from e
        except ProgrammingError as e:
            raise RuntimeError(f"SQL execution error: {str(e)}") from e

    def update_moodle_time(self, course_id: int, update_time: datetime = None) -> bool:
        """
        Update update_time_moodle for specified course
        :param course_id: Target course ID
        :param update_time: Specific time (default: current datetime)
        :return: True if update successful, False otherwise
        """
        if not update_time:
            update_time = datetime.now()

        sql = "UPDATE courses SET update_time_moodle = %s WHERE id = %s"
        try:
            with self.db_connector.get_connection() as conn:
                with conn.cursor() as cursor:
                    affected_rows = cursor.execute(sql, (update_time, course_id))
                    conn.commit()
                    return affected_rows > 0
        except ProgrammingError as e:
            raise RuntimeError(f"SQL execution error: {str(e)}") from e

    def update_exambase_time(
        self, course_id: int, update_time: datetime = None
    ) -> bool:
        """
        Update update_time_exambase for specified course
        :param course_id: Target course ID
        :param update_time: Specific time (default: current datetime)
        :return: True if update successful, False otherwise
        """
        if not update_time:
            update_time = datetime.now()

        sql = "UPDATE courses SET update_time_exambase = %s WHERE id = %s"
        try:
            with self.db_connector.get_connection() as conn:
                with conn.cursor() as cursor:
                    affected_rows = cursor.execute(sql, (update_time, course_id))
                    conn.commit()
                    return affected_rows > 0
        except ProgrammingError as e:
            raise RuntimeError(f"SQL execution error: {str(e)}") from e
