# python
# file: `dao/assignment.py` — updated imports (fixes NameError: timedelta)
from datetime import datetime, timezone, timedelta
from .connector import DBConnector
from typing import Optional, Any, List, Dict

# safe optional import of pymysql (environments may not have it)
try:
    import pymysql
    DictCursor = pymysql.cursors.DictCursor
except Exception:
    pymysql = None
    DictCursor = None


class AssignmentDAO:
    def __init__(self, connector: Optional[DBConnector] = None):
        self._connector = connector or DBConnector()
        self._pk_col: Optional[str] = None

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

    def _detect_pk_column(self, conn) -> str:
        if self._pk_col:
            return self._pk_col
        sql = """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'assignment'
        """
        cursor_args = (DictCursor,) if DictCursor else ()
        with conn.cursor(*cursor_args) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            cols = set()
            if rows:
                for r in rows:
                    row = self._row_to_dict(cur, r)
                    if row and 'COLUMN_NAME' in row:
                        cols.add(row['COLUMN_NAME'])
                    else:
                        if isinstance(r, (list, tuple)) and len(r) > 0:
                            cols.add(r[0])
        for candidate in ('id', 'assignment_id', 'assignmentId'):
            if candidate in cols:
                self._pk_col = candidate
                return self._pk_col
        self._pk_col = next(iter(cols)) if cols else 'id'
        return self._pk_col

    def _has_column(self, conn, colname: str) -> bool:
        sql = """
            SELECT 1
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'assignment'
              AND COLUMN_NAME = %s
            LIMIT 1
        """
        cursor_args = (DictCursor,) if DictCursor else ()
        with conn.cursor(*cursor_args) as cur:
            cur.execute(sql, (colname,))
            return cur.fetchone() is not None

    def count_pending_assignments(self, user_id: int, year: int, month: int) -> int:
        conn_candidate = self.get_connection()
        is_ctx = self._is_context_manager(conn_candidate)

        def _run(conn):
            cursor_args = (DictCursor,) if DictCursor else ()
            if self._has_column(conn, "user_id"):
                sql = """
                SELECT COUNT(1) AS cnt
                FROM assignment a
                WHERE a.user_id = %s
                  AND a.status != 'completed'
                  AND YEAR(a.due_date) = %s
                  AND MONTH(a.due_date) = %s
                """
                params = (user_id, year, month)
            else:
                sql = """
                SELECT COUNT(1) AS cnt
                FROM assignment a
                JOIN user_courses uc ON uc.course_id = a.course_id
                WHERE uc.user_id = %s
                  AND a.status != 'completed'
                  AND YEAR(a.due_date) = %s
                  AND MONTH(a.due_date) = %s
                """
                params = (user_id, year, month)

            with conn.cursor(*cursor_args) as cur:
                cur.execute(sql, params)
                row = cur.fetchone()
                rowd = self._row_to_dict(cur, row)
                return int((rowd and (rowd.get('cnt') or rowd.get('COUNT(1)'))) or 0)

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

    def find_one_pending_assignment(self, conn, user_id: int, year: int, month: int) -> Optional[int]:
        pk = self._detect_pk_column(conn)
        cursor_args = (DictCursor,) if DictCursor else ()
        if self._has_column(conn, "user_id"):
            sql = f"""
                SELECT a.`{pk}` AS assignment_id
                FROM assignment a
                WHERE a.user_id = %s
                  AND a.status != 'completed'
                  AND YEAR(a.due_date) = %s
                  AND MONTH(a.due_date) = %s
                LIMIT 1
            """
            params = (user_id, year, month)
        else:
            sql = f"""
                SELECT a.`{pk}` AS assignment_id
                FROM assignment a
                JOIN user_courses uc ON uc.course_id = a.course_id
                WHERE uc.user_id = %s
                  AND a.status != 'completed'
                  AND YEAR(a.due_date) = %s
                  AND MONTH(a.due_date) = %s
                LIMIT 1
            """
            params = (user_id, year, month)

        with conn.cursor(*cursor_args) as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            rowd = self._row_to_dict(cur, row)
            if rowd and rowd.get('assignment_id') is not None:
                return int(rowd['assignment_id'])
        return None
    # python
    # python
    def mark_complete(self, conn, assignment_id: int):
        """
        Debug variant: returns (updated: bool, rowcount: int, last_executed: Optional[str])
        Caller must commit/rollback.
        """
        pk = self._detect_pk_column(conn)
        sql = f"UPDATE assignment SET status = 'completed' WHERE `{pk}` = %s AND status != 'completed'"
        cursor_args = ()
        with conn.cursor(*cursor_args) as cur:
            cur.execute(sql, (assignment_id,))
            rowcount = getattr(cur, "rowcount", None)
            # many DB drivers expose the last executed SQL under different attributes
            last_executed = getattr(cur, "_last_executed", None) or getattr(cur, "last_executed", None)
            return (bool(rowcount and rowcount > 0), int(rowcount or 0), last_executed)
        
    def mark_pending(self, conn, assignment_id: int):
        """
        Debug variant: returns (updated: bool, rowcount: int, last_executed: Optional[str])
        Caller must commit/rollback.
        """
        pk = self._detect_pk_column(conn)
        sql = f"UPDATE assignment SET status = 'pending' WHERE `{pk}` = %s AND status != 'pending'"
        cursor_args = ()
        with conn.cursor(*cursor_args) as cur:
            cur.execute(sql, (assignment_id,))
            rowcount = getattr(cur, "rowcount", None)
            # many DB drivers expose the last executed SQL under different attributes
            last_executed = getattr(cur, "_last_executed", None) or getattr(cur, "last_executed", None)
            return (bool(rowcount and rowcount > 0), int(rowcount or 0), last_executed)

    # 在 AssignmentDAO 类中添加以下方法

    def get_assignments_by_date_range(self, user_id: int, start_date: datetime, end_date: datetime) -> List[Dict]:
        """获取用户在指定时间范围内的作业"""
        conn_candidate = self.get_connection()
        is_ctx = self._is_context_manager(conn_candidate)

        def _run(conn):
            cursor_args = (DictCursor,) if DictCursor else ()

            # 检查表结构
            has_user_id = self._has_column(conn, "user_id")

            if has_user_id:
                sql = """
                      SELECT a.id, \
                             a.title, \
                             a.description, \
                             a.course_id, \
                             a.due_date, \
                             a.status, \
                             a.assignment_type, \
                             a.max_score, \
                             a.instructions, \
                             c.course_name
                      FROM assignment a
                               LEFT JOIN courses c ON a.course_id = c.course_id
                      WHERE a.user_id = %s
                        AND a.due_date BETWEEN %s AND %s
                      ORDER BY a.due_date \
                      """
                params = (user_id, start_date, end_date)
            else:
                sql = """
                      SELECT a.id, \
                             a.title, \
                             a.description, \
                             a.course_id, \
                             a.due_date, \
                             a.status, \
                             a.assignment_type, \
                             a.max_score, \
                             a.instructions, \
                             c.course_name
                      FROM assignment a
                               LEFT JOIN courses c ON a.course_id = c.course_id
                               JOIN user_courses uc ON uc.course_id = a.course_id
                      WHERE uc.user_id = %s
                        AND a.due_date BETWEEN %s AND %s
                      ORDER BY a.due_date \
                      """
                params = (user_id, start_date, end_date)

            with conn.cursor(*cursor_args) as cur:
                cur.execute(sql, params)
                assignments = []
                for row in cur.fetchall():
                    row_dict = self._row_to_dict(cur, row)
                    if row_dict:
                        assignments.append(row_dict)
                return assignments

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

    def get_assignments_by_type(self, user_id: int, assignment_type: str, start_date: datetime = None,
                                end_date: datetime = None) -> List[Dict]:
        """根据类型获取用户的作业"""
        conn_candidate = self.get_connection()
        is_ctx = self._is_context_manager(conn_candidate)

        def _run(conn):
            cursor_args = (DictCursor,) if DictCursor else ()

            has_user_id = self._has_column(conn, "user_id")

            base_sql = """
                       SELECT a.id, \
                              a.title, \
                              a.description, \
                              a.course_id, \
                              a.due_date, \
                              a.status, \
                              a.assignment_type, \
                              a.max_score, \
                              a.instructions, \
                              c.course_name
                       FROM assignment a
                                LEFT JOIN courses c ON a.course_id = c.course_id \
                       """

            if has_user_id:
                base_sql += " WHERE a.user_id = %s AND a.assignment_type = %s"
                params = [user_id, assignment_type]
            else:
                base_sql += """
                    JOIN user_courses uc ON uc.course_id = a.course_id
                    WHERE uc.user_id = %s AND a.assignment_type = %s
                """
                params = [user_id, assignment_type]

            if start_date and end_date:
                base_sql += " AND a.due_date BETWEEN %s AND %s"
                params.extend([start_date, end_date])

            base_sql += " ORDER BY a.due_date"

            with conn.cursor(*cursor_args) as cur:
                cur.execute(base_sql, params)
                assignments = []
                for row in cur.fetchall():
                    row_dict = self._row_to_dict(cur, row)
                    if row_dict:
                        assignments.append(row_dict)
                return assignments

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

    # 在 AssignmentDAO 类中添加

    def get_assignment_progress_stats(self, user_id: int) -> Dict:
        """获取用户作业进度统计"""
        conn_candidate = self.get_connection()
        is_ctx = self._is_context_manager(conn_candidate)

        def _run(conn):
            cursor_args = (DictCursor,) if DictCursor else ()

            has_user_id = self._has_column(conn, "user_id")

            if has_user_id:
                sql = """
                      SELECT COUNT(*)                                                                      as total, \
                             SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END)                         as completed, \
                             SUM(CASE WHEN status != 'completed' AND status IS NOT NULL THEN 1 ELSE 0 END) as pending
                      FROM assignment
                      WHERE user_id = %s \
                      """
                params = (user_id,)
            else:
                sql = """
                      SELECT COUNT(*)                                                                          as total, \
                             SUM(CASE WHEN a.status = 'completed' THEN 1 ELSE 0 END)                           as completed, \
                             SUM(CASE WHEN a.status != 'completed' AND a.status IS NOT NULL THEN 1 ELSE 0 END) as pending
                      FROM assignment a
                               JOIN user_courses uc ON a.course_id = uc.course_id
                      WHERE uc.user_id = %s \
                      """
                params = (user_id,)

            with conn.cursor(*cursor_args) as cur:
                cur.execute(sql, params)
                result = cur.fetchone()
                row_dict = self._row_to_dict(cur, result)

                return {
                    'total': row_dict.get('total', 0) or 0,
                    'completed': row_dict.get('completed', 0) or 0,
                    'pending': row_dict.get('pending', 0) or 0
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

    def get_upcoming_assignments(self, user_id: int, days: int = 7) -> List[Dict]:
        """获取用户近期待办作业"""
        conn_candidate = self.get_connection()
        is_ctx = self._is_context_manager(conn_candidate)

        def _run(conn):
            cursor_args = (DictCursor,) if DictCursor else ()

            start_date = datetime.now()
            end_date = start_date + timedelta(days=days)

            has_user_id = self._has_column(conn, "user_id")

            if has_user_id:
                sql = """
                      SELECT a.id, \
                             a.title, \
                             a.due_date, \
                             a.status, \
                             a.assignment_type, \
                             c.course_name
                      FROM assignment a
                               LEFT JOIN courses c ON a.course_id = c.course_id
                      WHERE a.user_id = %s
                        AND a.due_date BETWEEN %s AND %s
                        AND a.status != 'completed'
                      ORDER BY a.due_date \
                      """
                params = (user_id, start_date, end_date)
            else:
                sql = """
                      SELECT a.id, \
                             a.title, \
                             a.due_date, \
                             a.status, \
                             a.assignment_type, \
                             c.course_name
                      FROM assignment a
                               LEFT JOIN courses c ON a.course_id = c.course_id
                               JOIN user_courses uc ON uc.course_id = a.course_id
                      WHERE uc.user_id = %s
                        AND a.due_date BETWEEN %s AND %s
                        AND a.status != 'completed'
                      ORDER BY a.due_date \
                      """
                params = (user_id, start_date, end_date)

            with conn.cursor(*cursor_args) as cur:
                cur.execute(sql, params)
                assignments = []
                for row in cur.fetchall():
                    row_dict = self._row_to_dict(cur, row)
                    if row_dict:
                        assignments.append({
                            'id': row_dict.get('id'),
                            'title': row_dict.get('title'),
                            'due_date': row_dict.get('due_date').strftime('%Y-%m-%d %H:%M') if row_dict.get(
                                'due_date') else None,
                            'course_name': row_dict.get('course_name'),
                            'assignment_type': row_dict.get('assignment_type'),
                            'status': row_dict.get('status')
                        })
                return assignments

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