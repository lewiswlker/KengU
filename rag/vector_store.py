from __future__ import annotations

import os
from typing import Dict, List, Tuple

import uuid


class ChromaVectorStore:
    """
    Chroma-based vector store with per-course collections.
    - Persistent directory controlled by 'persist_dir'
    - Collection name pattern: 'course_{course_id}'
    """

    def __init__(self, persist_dir: str):
        try:
            import chromadb  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError("chromadb is not installed. Please install chromadb.") from e
        os.makedirs(persist_dir, exist_ok=True)
        self._chroma = chromadb.PersistentClient(path=persist_dir)

    def _get_collection(self, course_id: int):
        name = f"course_{course_id}"
        # Default metric is cosine. You can change to L2 with metadata if needed:
        # metadata={"hnsw:space": "l2"}
        return self._chroma.get_or_create_collection(name=name)

    def add_chunks(self, course_id: int, vectors: List[List[float]], chunks: List[Dict]) -> None:
        if not vectors or not chunks:
            return
        if len(vectors) != len(chunks):
            raise ValueError("vectors and chunks length mismatch")
        col = self._get_collection(course_id)
        ids = [str(uuid.uuid4()) for _ in chunks]
        documents = [c.get("content_with_weight", "") for c in chunks]
        metadatas = [
            {
                "course_id": int(c.get("course_id", course_id)),
                "title": c.get("title", ""),
                "url": c.get("url", ""),
            }
            for c in chunks
        ]
        col.add(ids=ids, embeddings=vectors, metadatas=metadatas, documents=documents)

    def search(self, course_id: int, query_vector: List[float], top_k: int = 5) -> List[Tuple[Dict, float]]:
        col = self._get_collection(course_id)
        if col.count() == 0:
            return []
        res = col.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        # res fields: 'ids', 'documents', 'metadatas', 'distances' are lists with a single inner list
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        results: List[Tuple[Dict, float]] = []
        for doc, meta, dist in zip(docs, metas, dists):
            chunk = {
                "course_id": meta.get("course_id"),
                "title": meta.get("title", ""),
                "url": meta.get("url", ""),
                "content_with_weight": doc or "",
            }
            results.append((chunk, float(dist)))
        return results