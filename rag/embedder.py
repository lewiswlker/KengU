from __future__ import annotations

import os
from typing import List, Tuple
import requests


class Embedder:
    """
    Simple HTTP embedder supporting two modes:
    - openai: POST {model, input} -> {data:[{embedding:[]}]}
    - simple: POST {model, sentence} (one by one), returns {embedding: []}
    """

    def __init__(self):
        self.api_type = os.getenv("EMBEDDING_API_TYPE", "openai").lower()
        self.api_url = os.getenv("EMBEDDING_API_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings")
        self.api_key = os.getenv("EMBEDDING_API_KEY", "sk-4c8c2ca0523446288547f6bb2c72a9dc")
        self.model = os.getenv("EMBEDDING_MODEL", "text-embedding-v4")
        self.timeout_s = float(os.getenv("EMBEDDING_TIMEOUT_S", "30"))
        self.batch_size = int(os.getenv("EMBEDDING_BATCH_SIZE", "64"))
        self.max_chars = int(os.getenv("EMBEDDING_MAX_CHARS", "4000"))

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def embed_texts(self, texts: List[str]) -> Tuple[List[List[float]], int]:
        """
        Returns (embeddings, token_count_approx). Token count is optional best-effort.
        """
        if not texts:
            return [], 0
        if self.api_type == "openai":
            all_vecs: List[List[float]] = []
            # DashScope 单次批量上限 10
            effective_bs = min(self.batch_size, 10)
            for i in range(0, len(texts), effective_bs):
                batch = [t[:self.max_chars] for t in texts[i : i + effective_bs]]
                payload = {"model": self.model, "input": batch}
                resp = requests.post(
                    self.api_url, json=payload, headers=self._headers(), timeout=self.timeout_s
                )
                if resp.status_code != 200:
                    from requests import HTTPError
                    raise HTTPError(f"{resp.status_code} {resp.reason}: {resp.text}")
                data = resp.json().get("data", [])
                all_vecs.extend([item["embedding"] for item in data])
            return all_vecs, 0
        # simple mode: call one by one
        embeddings: List[List[float]] = []
        for t in texts:
            payload = {"model": self.model, "sentence": t[:self.max_chars]}
            resp = requests.post(
                self.api_url, json=payload, headers=self._headers(), timeout=self.timeout_s
            )
            resp.raise_for_status()
            embeddings.append(resp.json()["embedding"])
        return embeddings, 0


if __name__ == "__main__":
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(description="Quick test for Embedder.embed_texts")
    parser.add_argument(
        "--texts",
        type=str,
        default="这是一段测试文本;Embedding 功能验证",
        help="Use ';' to separate multiple texts",
    )
    args = parser.parse_args()

    texts = [t for t in args.texts.split(";") if t.strip()]
    if not texts:
        print("No input texts provided.", file=sys.stderr)
        sys.exit(2)

    emb = Embedder()
    print(f"[Embedder] api_type={emb.api_type} api_url={emb.api_url} model={emb.model}")
    try:
        vectors, _ = emb.embed_texts(texts)
        print(f"Embedded {len(vectors)} texts.")
        if vectors:
            dim = len(vectors[0])
            print(f"Vector dim: {dim}")
            print("First vector (first 8 dims):", json.dumps(vectors[0][:8]))
    except Exception as e:
        print(f"Embedding failed: {e}", file=sys.stderr)
        sys.exit(1)

