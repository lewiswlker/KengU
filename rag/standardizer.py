from __future__ import annotations

import os
from pathlib import Path
from typing import List, Dict


def _html_to_text(html: str) -> str:
    try:
        from bs4 import BeautifulSoup  # type: ignore
    except Exception:
        # Fallback: naive tag strip
        import re

        return re.sub(r"<[^>]+>", " ", html or "").strip()
    soup = BeautifulSoup(html or "", "html.parser")
    return soup.get_text("\n", strip=True)


def _pdf_to_text(path: str) -> str:
    try:
        from PyPDF2 import PdfReader  # type: ignore
    except Exception as e:
        raise RuntimeError("PyPDF2 未安装，无法解析 PDF") from e
    text = ""
    with open(path, "rb") as f:
        reader = PdfReader(f)
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"
    return text


def _read_file_text(path: str) -> str:
    p = Path(path)
    suf = p.suffix.lower()
    if suf in [".txt", ".md"]:
        return p.read_text(encoding="utf-8", errors="ignore")
    if suf in [".html", ".htm"]:
        return _html_to_text(p.read_text(encoding="utf-8", errors="ignore"))
    if suf == ".pdf":
        return _pdf_to_text(str(p))
    return ""


def standardize_items(items: List[Dict]) -> List[Dict]:
    """
    输入 items，每项可包含：title、url、text、html、path
    输出标准文档：{title, url, content}
    """
    docs: List[Dict] = []
    for it in items or []:
        title = (it.get("title") or "").strip()
        url = (it.get("url") or "").strip()
        content = (it.get("text") or "").strip()
        if not content:
            html = it.get("html")
            if html:
                content = _html_to_text(html)
        if not content:
            path = it.get("path")
            if path:
                content = _read_file_text(path)
                if not url:
                    url = f"file://{path}"
        if content:
            docs.append({"title": title, "url": url, "content": content})
    return docs