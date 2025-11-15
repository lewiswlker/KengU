from __future__ import annotations

from typing import Iterable, List, Dict, Tuple
import re

class RecursiveDocumentChunker:
    """
    Structure-aware chunker for English documents.
    - Honors document structure markers inserted by standardizer:
      "=== Slide N ===", "=== Page N ===", and heading lines starting with '#' (1-6).
    - Packs content to target token size, with sentence-aware boundaries and overlap.
    """

    def __init__(
        self,
        target_tokens: int = 1024,
        max_tokens: int = 1536,
        min_tokens: int = 200,
        overlap_tokens: int = 150,
        token_chars_ratio: float = 4.0,
    ):
        if not (0 < min_tokens <= target_tokens <= max_tokens):
            raise ValueError("Require 0 < min_tokens <= target_tokens <= max_tokens")
        if overlap_tokens < 0 or overlap_tokens >= target_tokens:
            raise ValueError("overlap_tokens must be in [0, target_tokens)")
        self.target_tokens = target_tokens
        self.max_tokens = max_tokens
        self.min_tokens = min_tokens
        self.overlap_tokens = overlap_tokens
        # Approximate English token length to characters if tokenizer not provided
        self.token_chars_ratio = token_chars_ratio

        # Precompiled patterns
        self._re_slide = re.compile(r"^===\s*Slide\s+\d+\s*===$", re.IGNORECASE)
        self._re_page = re.compile(r"^===\s*Page\s+\d+\s*===$", re.IGNORECASE)
        self._re_heading = re.compile(r"^(#{1,6})\s+(.+)")
        self._re_sentence = re.compile(r"(?<=[\.!\?])\s+")

    def _tokens_to_chars(self, tokens: int) -> int:
        return int(tokens * self.token_chars_ratio)

    def _split_by_markers(self, text: str) -> List[Tuple[str, str]]:
        """
        Split into top-level blocks by Slide or Page markers if present.
        Returns list of (marker, block_text). marker may be "SLIDE", "PAGE", or "DOC".
        """
        lines = (text or "").splitlines()
        if not lines:
            return []
        blocks: List[Tuple[str, str]] = []
        current: List[str] = []
        current_kind = "DOC"
        for ln in lines:
            if self._re_slide.match(ln.strip()):
                if current:
                    blocks.append((current_kind, "\n".join(current).strip()))
                    current = []
                current_kind = "SLIDE"
                # keep marker as a title anchor inside block
                current.append(ln)
                continue
            if self._re_page.match(ln.strip()):
                if current:
                    blocks.append((current_kind, "\n".join(current).strip()))
                    current = []
                current_kind = "PAGE"
                current.append(ln)
                continue
            current.append(ln)
        if current:
            blocks.append((current_kind, "\n".join(current).strip()))
        # If no explicit markers found, one DOC block
        if len(blocks) == 1 and blocks[0][0] == "DOC":
            return blocks
        # Filter empty blocks
        return [(k, b) for k, b in blocks if b.strip()]

    def _split_headings(self, block_text: str) -> List[Tuple[int, str]]:
        """
        Split block by heading lines (# ...). Returns list of (level, section_text).
        If no headings found, returns single (7, block_text) where 7 means 'body'.
        """
        lines = block_text.splitlines()
        sections: List[Tuple[int, List[str]]] = []
        current_level = 7
        current_lines: List[str] = []
        for ln in lines:
            m = self._re_heading.match(ln.strip())
            if m:
                # flush previous
                if current_lines:
                    sections.append((current_level, current_lines))
                    current_lines = []
                level = len(m.group(1))
                current_level = level
                current_lines.append(ln)
            else:
                current_lines.append(ln)
        if current_lines:
            sections.append((current_level, current_lines))
        # merge trivial empty sections
        merged: List[Tuple[int, str]] = []
        for lvl, arr in sections:
            txt = "\n".join(arr).strip()
            if txt:
                merged.append((lvl, txt))
        if not merged:
            return [(7, block_text)]
        return merged

    def _paragraphs(self, text: str) -> List[str]:
        # Paragraph by double newline; fallback single
        parts = re.split(r"\n\s*\n", text.strip())
        parts = [p.strip() for p in parts if p.strip()]
        if parts:
            return parts
        parts = [t.strip() for t in text.splitlines() if t.strip()]
        return parts if parts else [text.strip()]

    def _sentences(self, text: str) -> List[str]:
        # Sentence split; keep punctuation with sentence
        text = " ".join(text.split())
        if not text:
            return []
        arr = self._re_sentence.split(text)
        return [s.strip() for s in arr if s.strip()]

    def _pack(self, fragments: List[str]) -> List[str]:
        """
        Pack fragments (sentence-level) to target/max with char-based approximation.
        Applies overlap by carrying tail content into next chunk start.
        """
        target = self._tokens_to_chars(self.target_tokens)
        max_len = self._tokens_to_chars(self.max_tokens)
        min_len = self._tokens_to_chars(self.min_tokens)
        overlap = self._tokens_to_chars(self.overlap_tokens)

        chunks: List[str] = []
        buf: List[str] = []
        buf_len = 0
        for frag in fragments:
            frag_len = len(frag)
            if buf_len == 0:
                buf.append(frag)
                buf_len = frag_len
                continue
            if buf_len + 1 + frag_len <= max_len:
                buf.append(frag)
                buf_len += 1 + frag_len
                if buf_len >= target:
                    chunks.append(" ".join(buf).strip())
                    # overlap handling: take tail substring as new seed
                    tail = chunks[-1][-overlap:] if overlap > 0 else ""
                    buf = [tail] if tail else []
                    buf_len = len(tail)
            else:
                if buf_len >= min_len:
                    chunks.append(" ".join(buf).strip())
                    tail = chunks[-1][-overlap:] if overlap > 0 else ""
                    buf = [tail] if tail else []
                    buf_len = len(tail)
                    # re-process current frag into new buf
                    if frag_len >= max_len:
                        # Hard split this very long fragment
                        start = 0
                        while start < frag_len:
                            end = min(start + max_len, frag_len)
                            piece = frag[start:end]
                            if piece.strip():
                                chunks.append(piece.strip())
                            start = end - overlap if end < frag_len else end
                        buf = []
                        buf_len = 0
                    else:
                        buf.append(frag)
                        buf_len = len(frag)
                else:
                    # force split early if buffer is too small but next frag would overflow
                    if buf:
                        chunks.append(" ".join(buf).strip())
                    tail = chunks[-1][-overlap:] if overlap > 0 and chunks else ""
                    buf = [tail, frag] if tail else [frag]
                    buf_len = len(" ".join(buf))

        if buf_len > 0:
            # if last is too small, try to merge back with previous if reasonable
            if chunks and buf_len < min_len and len(chunks[-1]) + 1 + buf_len <= max_len:
                chunks[-1] = (chunks[-1] + " " + " ".join(buf)).strip()
            else:
                chunks.append(" ".join(buf).strip())

        return [c for c in chunks if c.strip()]

    def chunk(self, text: str) -> List[str]:
        content = (text or "").strip()
        if not content:
            return []
        result: List[str] = []
        top_blocks = self._split_by_markers(content)
        if not top_blocks:
            top_blocks = [("DOC", content)]

        for _, block in top_blocks:
            # split by headings if available
            sections = self._split_headings(block)
            section_texts = [sec for _, sec in sections] if sections else [block]
            # drill down to paragraphs then sentences
            sentences: List[str] = []
            for sec in section_texts:
                for para in self._paragraphs(sec):
                    sents = self._sentences(para)
                    if not sents:
                        continue
                    sentences.extend(sents)
            if not sentences:
                sentences = self._sentences(block)
            if not sentences:
                sentences = [block]
            result.extend(self._pack(sentences))
        return result


def build_chunks_from_docs(
    docs: Iterable[Dict[str, str]], chunker
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