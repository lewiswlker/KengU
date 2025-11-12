from __future__ import annotations

from typing import Iterable, List, Dict


class FixedChunker:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be in [0, chunk_size)")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, text: str) -> List[str]:
        content = (text or "").strip()
        if not content:
            return []
        result: List[str] = []
        start = 0
        while start < len(content):
            end = min(start + self.chunk_size, len(content))
            result.append(content[start:end])
            if end == len(content):
                break
            start = end - self.chunk_overlap
        return result


def build_chunks_from_docs(
    docs: Iterable[Dict[str, str]], chunker: FixedChunker
) -> List[Dict]:
    """
    Convert raw documents to chunk dicts with basic metadata.
    Each input doc expects keys: title, url, content, course_id.
    """
    chunks: List[Dict] = []
    for d in docs:
        course_id = int(d["course_id"])
        title = (d.get("title") or "").strip()
        url = (d.get("url") or "").strip()
        content = d.get("content") or ""
        for seg in chunker.chunk(content):
            chunks.append(
                {
                    "course_id": course_id,
                    "title": title,
                    "url": url,
                    "content_with_weight": seg,
                }
            )
    return chunks