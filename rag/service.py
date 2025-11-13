from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from dao import CourseDAO
from .chunker import RecursiveDocumentChunker, build_chunks_from_docs
from .embedder import Embedder
from .vector_store import ChromaVectorStore
from .retriever import Retriever


class RagService:
    """
    Orchestrates ingestion, retrieval and generation for course-based RAG.
    """

    def __init__(self):
        index_dir = os.getenv("INDEX_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "vectorbase"))
        # Always use document-structure-aware chunker
        self.chunker = RecursiveDocumentChunker(
            target_tokens=int(os.getenv("TARGET_TOKENS", "1024")),
            max_tokens=int(os.getenv("MAX_TOKENS", "1536")),
            min_tokens=int(os.getenv("MIN_TOKENS", "200")),
            overlap_tokens=int(os.getenv("OVERLAP_TOKENS", "150")),
            token_chars_ratio=float(os.getenv("TOKEN_CHARS_RATIO", "4.0")),
        )
        self.embedder = Embedder()
        self.store = ChromaVectorStore(persist_dir=index_dir)
        self.retriever = Retriever(self.store, self.embedder)
        self.course_dao = CourseDAO()

    def _find_kb_root(self, file_path: "Path") -> "Path":
        """
        尝试向上查找名为 knowledge_base 的目录作为根；找不到则回退到 file_path.parent.parent。
        """
        p = file_path.resolve()
        for parent in p.parents:
            if parent.name == "knowledge_base":
                return parent
        # 回退：课程目录父级
        return p.parent.parent

    def build_http_url(self, base_url: str, file_path: str) -> str:
        """
        将 knowledge_base 下文件路径转换为可下载的 HTTP 链接：
        url = base_url + urlencoded(rel_path_from_kb_root)
        """
        from pathlib import Path
        import urllib.parse

        fp = Path(file_path).resolve()
        kb_root = self._find_kb_root(fp)
        rel = fp.relative_to(kb_root)
        rel_url = urllib.parse.quote(str(rel).replace(os.sep, "/"))
        return urllib.parse.urljoin(base_url.rstrip("/") + "/", rel_url)

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

    def ingest_file(self, course_id: int, file_path: str, base_url: str) -> Dict:
        """
        单文件入库：读取文件文本，构造 url，标准化为文档后调用 ingest。
        """
        from pathlib import Path
        from .standardizer import standardize_items

        fp = Path(file_path).resolve()
        item = {
            "title": fp.stem,
            "url": self.build_http_url(base_url, str(fp)),
            "path": str(fp),
        }
        docs = standardize_items([item])
        if not docs:
            raise RuntimeError("标准化结果为空，请检查文件类型与解析依赖")
        return self.ingest(course_id=course_id, documents=docs)

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


if __name__ == "__main__":
    import argparse
    import json
    import sys

    # # 简化版：单文件入库 + 检索 + 输出（与 full_pipeline_test 等价的最小链路）
    # parser = argparse.ArgumentParser(description="RagService demo: 单文件入库 + 检索")
    # parser.add_argument("--course_id", type=int, required=True, help="Course ID")
    # parser.add_argument("--file_path", type=str, required=True, help="knowledge_base 下单个文件的绝对路径")
    # parser.add_argument("--base_url", type=str, default="http://127.0.0.1:8009/", help="静态服务根地址（映射到 knowledge_base）")
    # parser.add_argument("--query", type=str, required=True, help="检索问题")
    # parser.add_argument("--top_k", type=int, default=6, help="Top K")
    # args = parser.parse_args()

    # print("[说明] 当前为简化示例：单文件入库 -> 检索 -> 输出；自动化入库尚未实现。")

    # try:
    #     svc = RagService()
    #     # 1) 单文件入库（内部：构造 URL + 标准化 + chunk + embedding + 写入 Chroma）
    #     stats = svc.ingest_file(course_id=args.course_id, file_path=args.file_path, base_url=args.base_url)
    #     print("[Ingest] 入库:", json.dumps(stats, ensure_ascii=False))

    #     # 2) 检索
    #     hits = svc.retrieve_for_courses(args.query, [args.course_id], top_k=args.top_k)
    #     print(f"[Retrieve] 命中: {len(hits)}")
    #     for i, r in enumerate(hits, 1):
    #         preview = (r.get("text") or "")[:80].replace("\n", " ")
    #         out = {
    #             "idx": i,
    #             "title": r.get("title"),
    #             "url": r.get("url"),
    #             "relevance": r.get("relevance"),
    #             "preview": preview,
    #         }
    #         print(json.dumps(out, ensure_ascii=False))
    # except Exception as e:
    #     print(f"RagService demo failed: {e}", file=sys.stderr)
    #     sys.exit(1)