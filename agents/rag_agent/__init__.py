"""
RAG Agent Package
Provides RAG-based question answering with course-specific retrieval
"""

from .rag_agent import answer_with_rag, RetrievalResult

__all__ = ["answer_with_rag", "RetrievalResult"]
