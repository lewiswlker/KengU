# python
from typing import List, Dict, Optional
from pymysql.err import ProgrammingError, IntegrityError
from .connector import DBConnector


class AgentInteractionDAO:
    """Data Access Object for agent_interactions table"""
    def __init__(self):
        self.db_connector = DBConnector()

    def find_by_id(self, interaction_id: int) -> Optional[Dict]:
        """Find agent interaction by ID"""
        sql = """
            SELECT id, user_id, user_message, retrieved_documents, ai_response,
                   ai_model, user_feedback, user_rating, is_helpful, created_at
            FROM agent_interactions
            WHERE id = %s
            LIMIT 1
        """
        try:
            with self.db_connector.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (interaction_id,))
                    return cursor.fetchone()
        except ProgrammingError as e:
            raise RuntimeError(f"SQL execution error: {str(e)}") from e

    def find_by_user_id(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Find all agent interactions for a user (most recent first)"""
        sql = """
            SELECT id, user_id, user_message, retrieved_documents, ai_response,
                   ai_model, user_feedback, user_rating, is_helpful, created_at
            FROM agent_interactions
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        try:
            with self.db_connector.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (user_id, limit))
                    return cursor.fetchall()
        except ProgrammingError as e:
            raise RuntimeError(f"SQL execution error: {str(e)}") from e

    def insert(self, user_id: int, user_message: str, ai_response: str,
               ai_model: Optional[str] = None, retrieved_documents: Optional[str] = None) -> Optional[int]:
        """Insert new agent interaction"""
        sql = """
            INSERT INTO agent_interactions
            (user_id, user_message, ai_response, ai_model, retrieved_documents)
            VALUES (%s, %s, %s, %s, %s)
        """
        try:
            with self.db_connector.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (user_id, user_message, ai_response, ai_model, retrieved_documents))
                    conn.commit()
                    return cursor.lastrowid
        except IntegrityError as e:
            raise RuntimeError(f"Integrity error: {str(e)}") from e
        except ProgrammingError as e:
            raise RuntimeError(f"SQL execution error: {str(e)}") from e

    def update_feedback(self, interaction_id: int, user_feedback: Optional[str] = None,
                       user_rating: Optional[int] = None, is_helpful: Optional[bool] = None) -> bool:
        """Update user feedback for an interaction"""
        sql = """
            UPDATE agent_interactions
            SET user_feedback = %s, user_rating = %s, is_helpful = %s
            WHERE id = %s
        """
        try:
            with self.db_connector.get_connection() as conn:
                with conn.cursor() as cursor:
                    affected_rows = cursor.execute(sql, (user_feedback, user_rating, is_helpful, interaction_id))
                    conn.commit()
                    return affected_rows > 0
        except ProgrammingError as e:
            raise RuntimeError(f"SQL execution error: {str(e)}") from e

    def delete(self, interaction_id: int) -> bool:
        """Delete agent interaction by ID"""
        sql = "DELETE FROM agent_interactions WHERE id = %s"
        try:
            with self.db_connector.get_connection() as conn:
                with conn.cursor() as cursor:
                    affected_rows = cursor.execute(sql, (interaction_id,))
                    conn.commit()
                    return affected_rows > 0
        except ProgrammingError as e:
            raise RuntimeError(f"SQL execution error: {str(e)}") from e