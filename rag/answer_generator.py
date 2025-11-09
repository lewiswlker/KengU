from __future__ import annotations

import os
from typing import List, Dict
import requests


class AnswerGenerator:
    """
    Simple OpenAI-compatible chat client to generate an answer using retrieved contexts.
    """

    def __init__(self):
        self.api_url = os.getenv("LLM_API_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")
        self.api_key = os.getenv("LLM_API_KEY", "sk-4c8c2ca0523446288547f6bb2c72a9dc")
        self.model = os.getenv("LLM_MODEL", "qwen-plus")
        self.timeout_s = float(os.getenv("LLM_TIMEOUT_S", "60"))

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def build_context_block(self, retrieved: List[Dict]) -> str:
        lines = []
        for i, r in enumerate(retrieved, 1):
            title = r.get("title") or ""
            url = r.get("source_url") or ""
            text = r.get("text") or ""
            lines.append(f"[{i}] {title} {url}\n{text}")
        return "\n\n".join(lines)

    def answer(self, query: str, retrieved: List[Dict]) -> str:
        if not retrieved:
            return "No relevant course content was found. Please specify the course more clearly or try again."
        context_block = self.build_context_block(retrieved)
        prompt = (
            "You are a course Q&A assistant. Please answer the question based solely on the provided course material snippets. "
            "Be sure to provide a concise and clear answer, and cite the snippet number as a reference when necessary.\n\n"
            f"[Reference Material Snippets]\n{context_block}\n\n"
            f"[User Question]\n{query}"
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a professional teaching assistant for course Q&A."},
                {"role": "user", "content": prompt},
            ],
            "temperature": float(os.getenv("LLM_TEMPERATURE", "0.3")),
        }
        resp = requests.post(
            self.api_url, json=payload, headers=self._headers(), timeout=self.timeout_s
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()