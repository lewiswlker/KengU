# study_session_dao.py
# python
from typing import Optional, Any, List, Dict
from datetime import datetime, timedelta

from .connector import DBConnector

# safe optional import of pymysql (environments may not have it)
try:
    import pymysql
    DictCursor = pymysql.cursors.DictCursor
except Exception:
    pymysql = None
    DictCursor = None

class StudySessionDAO:
    def __init__(self, connector: Optional[DBConnector] = None):
        self._connector = connector or DBConnector()

    def get_connection(self):
        return self._connector.get_connection()

    def _is_context_manager(self, obj) -> bool:
        return hasattr(obj, "__enter__") and hasattr(obj, "__exit__")

    def _row_to_dict(self, cur, row) -> Optional[dict]:
        if row is None:
            return None
        try:
            if hasattr(row, "keys"):
                return dict(row)
        except Exception:
            pass
        if hasattr(cur, "description") and cur.description:
            cols = [col[0] for col in cur.description]
            return dict(zip(cols, row))
        return {str(i): v for i, v in enumerate(row)}

    def get_study_sessions_by_date_range(self, user_id: int, start_date: datetime, end_date: datetime) -> List[Dict]:
        """获取用户在指定时间范围内的学习会话"""
        conn_candidate = self.get_connection()
        is_ctx = self._is_context_manager(conn_candidate)

        def _run(conn):
            cursor_args = (DictCursor,) if DictCursor else ()

            sql = """
                  SELECT ss.session_id, \
                         ss.assignment_id, \
                         ss.start_time, \
                         ss.duration_minutes, \
                         ss.notes, \
                         a.title as assignment_title, \
                         c.course_name
                  FROM study_sessions ss
                           LEFT JOIN assignment a ON ss.assignment_id = a.id
                           LEFT JOIN courses c ON a.course_id = c.id
                  WHERE ss.start_time BETWEEN %s AND %s
                    AND EXISTS (SELECT 1 \
                                FROM user_courses uc \
                                WHERE uc.user_id = %s \
                                  AND uc.course_id = c.id)
                  ORDER BY ss.start_time \
                  """
            params = (start_date, end_date, user_id)

            with conn.cursor(*cursor_args) as cur:
                cur.execute(sql, params)
                sessions = []
                for row in cur.fetchall():
                    row_dict = self._row_to_dict(cur, row)
                    if row_dict:
                        sessions.append(row_dict)
                return sessions

        if is_ctx:
            with conn_candidate as conn:
                return _run(conn)
        else:
            conn = conn_candidate
            try:
                return _run(conn)
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

    def get_study_sessions_by_course(self, user_id: int, course_id: int, start_date: datetime = None,
                                     end_date: datetime = None) -> List[Dict]:
        """获取用户指定课程的学习会话"""
        conn_candidate = self.get_connection()
        is_ctx = self._is_context_manager(conn_candidate)

        def _run(conn):
            cursor_args = (DictCursor,) if DictCursor else ()

            sql = """
                  SELECT ss.session_id, \
                         ss.assignment_id, \
                         ss.start_time, \
                         ss.duration_minutes, \
                         ss.notes, \
                         a.title as assignment_title, \
                         c.course_name
                  FROM study_sessions ss
                           LEFT JOIN assignment a ON ss.assignment_id = a.id
                           LEFT JOIN courses c ON a.course_id = c.id
                  WHERE c.id = %s
                    AND EXISTS (SELECT 1 \
                                FROM user_courses uc \
                                WHERE uc.user_id = %s \
                                  AND uc.course_id = c.id) \
                  """
            params = [course_id, user_id]

            if start_date and end_date:
                sql += " AND ss.start_time BETWEEN %s AND %s"
                params.extend([start_date, end_date])

            sql += " ORDER BY ss.start_time"

            with conn.cursor(*cursor_args) as cur:
                cur.execute(sql, params)
                sessions = []
                for row in cur.fetchall():
                    row_dict = self._row_to_dict(cur, row)
                    if row_dict:
                        sessions.append(row_dict)
                return sessions

        if is_ctx:
            with conn_candidate as conn:
                return _run(conn)
        else:
            conn = conn_candidate
            try:
                return _run(conn)
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

    # 在 StudySessionDAO 类中添加

    def get_study_session_stats(self, user_id: int, days: int = 30) -> Dict:
        """获取用户学习会话统计"""
        conn_candidate = self.get_connection()
        is_ctx = self._is_context_manager(conn_candidate)

        def _run(conn):
            cursor_args = (DictCursor,) if DictCursor else ()

            start_date = datetime.now() - timedelta(days=days)

            sql = """
                  SELECT COUNT(*)                           as total_sessions, \
                         SUM(COALESCE(duration_minutes, 0)) as total_minutes, \
                         AVG(COALESCE(duration_minutes, 0)) as avg_duration, \
                         COUNT(DISTINCT DATE (start_time))  as active_days
                  FROM study_sessions ss
                           LEFT JOIN assignment a ON ss.assignment_id = a.id
                  WHERE ss.start_time >= %s
                    AND EXISTS (SELECT 1 \
                                FROM user_courses uc \
                                WHERE uc.user_id = %s \
                                  AND uc.course_id = COALESCE(a.course_id, 0)) \
                  """
            params = (start_date, user_id)

            with conn.cursor(*cursor_args) as cur:
                cur.execute(sql, params)
                result = cur.fetchone()
                row_dict = self._row_to_dict(cur, result)

                total_minutes = row_dict.get('total_minutes', 0) or 0
                total_hours = total_minutes / 60

                return {
                    'total_sessions': row_dict.get('total_sessions', 0) or 0,
                    'total_study_hours': round(total_hours, 1),
                    'avg_duration': round(row_dict.get('avg_duration', 0) or 0, 1),
                    'active_days': row_dict.get('active_days', 0) or 0,
                    'period_days': days
                }

        if is_ctx:
            with conn_candidate as conn:
                return _run(conn)
        else:
            conn = conn_candidate
            try:
                return _run(conn)
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

    # New method to add a study session
    def add_study_session(self, assignment_id: int, start_time: datetime, duration_minutes: int, notes: str = None) -> int:
        """Insert a study session record and return the new session id (if DB returns one) or 1 for success.

        Note: The study_sessions table is expected to have an auto-increment primary key `session_id`.
        """
        conn_candidate = self.get_connection()
        is_ctx = self._is_context_manager(conn_candidate)

        def _run(conn):
            cursor_args = (DictCursor,) if DictCursor else ()
            sql = """
                INSERT INTO study_sessions (assignment_id, start_time, duration_minutes, notes)
                VALUES (%s, %s, %s, %s)
            """
            params = (assignment_id, start_time, duration_minutes, notes)
            with conn.cursor(*cursor_args) as cur:
                cur.execute(sql, params)
                conn.commit()  # Add commit here
                # attempt to return lastrowid if available
                lastid = getattr(cur, 'lastrowid', None)
                return int(lastid) if lastid is not None else 1

        if is_ctx:
            with conn_candidate as conn:
                return _run(conn)
        else:
            conn = conn_candidate
            try:
                return _run(conn)
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

    # New method to delete a study session by assignment title and user
    def delete_study_session_by_title(self, assignment_title: str, user_id: int) -> bool:
        """Delete study session by assignment title for user. Returns True if deleted."""
        conn_candidate = self.get_connection()
        is_ctx = self._is_context_manager(conn_candidate)

        def _run(conn):
            cursor_args = (DictCursor,) if DictCursor else ()
            sql = """
                DELETE ss FROM study_sessions ss
                JOIN assignment a ON ss.assignment_id = a.id
                WHERE a.title = %s
                  AND EXISTS (SELECT 1 FROM user_courses uc WHERE uc.user_id = %s AND uc.course_id = a.course_id)
            """
            params = (assignment_title, user_id)
            with conn.cursor(*cursor_args) as cur:
                cur.execute(sql, params)
                conn.commit()
                return cur.rowcount > 0

        if is_ctx:
            with conn_candidate as conn:
                return _run(conn)
        else:
            conn = conn_candidate
            try:
                return _run(conn)
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

    # New method to delete study session by id
    def delete_study_session_by_id(self, session_id: int) -> bool:
        """Delete study session by session_id. Returns True if deleted."""
        conn_candidate = self.get_connection()
        is_ctx = self._is_context_manager(conn_candidate)

        def _run(conn):
            cursor_args = (DictCursor,) if DictCursor else ()
            sql = "DELETE FROM study_sessions WHERE session_id = %s"
            params = (session_id,)
            with conn.cursor(*cursor_args) as cur:
                cur.execute(sql, params)
                conn.commit()
                return cur.rowcount > 0

        if is_ctx:
            with conn_candidate as conn:
                return _run(conn)
        else:
            conn = conn_candidate
            try:
                return _run(conn)
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
