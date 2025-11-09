from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

from ..dao.course import CourseDAO
from .chunker import FixedChunker, build_chunks_from_docs
from .embedder import Embedder
from .vector_store import ChromaVectorStore
from .retriever import Retriever
from .answer_generator import AnswerGenerator


class RagService:
    """
    Orchestrates ingestion, retrieval and generation for course-based RAG.
    """

    def __init__(self):
        index_dir = os.getenv("INDEX_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "vectorbase"))
        self.chunker = FixedChunker(
            chunk_size=int(os.getenv("CHUNK_SIZE", "500")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "100")),
        )
        self.embedder = Embedder()
        self.store = ChromaVectorStore(persist_dir=index_dir)
        self.retriever = Retriever(self.store, self.embedder)
        self.generator = AnswerGenerator()
        self.course_dao = CourseDAO()

    def ingest(self, course_id: int, documents: List[Dict]) -> Dict:
        """
        Ingest standardized documents for a course.
        Each doc expects keys: title, url, content.
        """
        if not documents:
            return {"course_id": course_id, "chunks": 0, "vectors_added": 0}
        # attach course_id
        for d in documents:
            d["course_id"] = course_id
        chunks = build_chunks_from_docs(documents, self.chunker)
        texts = [c["content_with_weight"] for c in chunks]
        vectors, _ = self.embedder.embed_texts(texts)
        self.store.add_chunks(course_id=course_id, vectors=vectors, chunks=chunks)
        return {"course_id": course_id, "chunks": len(chunks), "vectors_added": len(vectors)}

    def _course_names_to_ids(self, course_names: List[str]) -> List[int]:
        ids: List[int] = []
        for name in course_names:
            cid = self.course_dao.find_id_by_name(name)
            if cid is not None:
                ids.append(int(cid))
        # deduplicate stable
        seen = set()
        uniq: List[int] = []
        for c in ids:
            if c not in seen:
                uniq.append(c)
                seen.add(c)
        return uniq

    def retrieve(self, query: str, course_names: List[str], top_k: int = 6) -> List[Dict]:
        # typing alias: keep compatibility
        return self.retrieve_for_courses(query, self._course_names_to_ids(course_names), top_k=top_k)

    def retrieve_for_courses(self, query: str, course_ids: List[int], top_k: int = 6) -> List[Dict]:
        return self.retriever.retrieve_by_courses(query, course_ids, top_k=top_k)

    def retrieve_and_answer(self, query: str, course_names: List[str], top_k: int = 6) -> Tuple[str, List[Dict]]:
        course_ids = self._course_names_to_ids(course_names)
        retrieved = self.retriever.retrieve_by_courses(query, course_ids, top_k=top_k)
        answer = self.generator.answer(query, retrieved)
        return answer, retrieved