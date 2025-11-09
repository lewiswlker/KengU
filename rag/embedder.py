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
            payload = {"model": self.model, "input": texts}
            resp = requests.post(
                self.api_url, json=payload, headers=self._headers(), timeout=self.timeout_s
            )
            resp.raise_for_status()
            data = resp.json().get("data", [])
            embeddings = [item["embedding"] for item in data]
            return embeddings, 0
        # simple mode: call one by one
        embeddings: List[List[float]] = []
        for t in texts:
            payload = {"model": self.model, "sentence": t}
            resp = requests.post(
                self.api_url, json=payload, headers=self._headers(), timeout=self.timeout_s
            )
            resp.raise_for_status()
            embeddings.append(resp.json()["embedding"])
        return embeddings, 0