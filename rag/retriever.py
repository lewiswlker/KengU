from __future__ import annotations

from typing import Dict, List, Tuple
from urllib.parse import urlparse, unquote
import os

from .embedder import Embedder
from .vector_store import ChromaVectorStore


class Retriever:
    def __init__(self, store: ChromaVectorStore, embedder: Embedder):
        self.store = store
        self.embedder = embedder

    def retrieve_by_courses(
        self, query: str, course_ids: List[int], top_k: int = 6
    ) -> List[Dict]:
        if not course_ids:
            return []
        vectors, _ = self.embedder.embed_texts([query])
        if not vectors:
            return []
        qv = vectors[0]
        all_hits: List[Tuple[Dict, float]] = []
        for cid in course_ids:
            all_hits.extend(self.store.search(cid, qv, top_k=top_k))
        # sort by ascending distance (L2)
        all_hits.sort(key=lambda x: x[1])
        # convert to output
        results: List[Dict] = []
        for chunk, dist in all_hits[:top_k]:
            # Resolve URL and file extension
            url = chunk.get("url")
            try:
                path = unquote(urlparse(url).path or "")
                _, ext = os.path.splitext(path)
                ext = (ext or "").lower()
            except Exception:
                ext = ""
            title = chunk.get("title", "") or ""
            if ext and not title.lower().endswith(ext):
                title = f"{title}{ext}"
            results.append(
                {
                    "text": chunk["content_with_weight"],
                    "url": url,
                    "title": title,
                    "course_id": chunk.get("course_id"),
                    "score": float(dist),              # 距离
                    "relevance": 1.0 / (1.0 + float(dist)),  # 相关性映射到 (0,1]
                }
            )
        return results