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
    # Primary: PyPDF2
    try:
        from PyPDF2 import PdfReader  # type: ignore
        text = ""
        with open(path, "rb") as f:
            reader = PdfReader(f)
            for page in reader.pages:
                text += (page.extract_text() or "") + "\n"
        if text.strip():
            return text
    except Exception:
        pass
    # Fallback: PyMuPDF (fitz) if available
    try:
        import fitz  # type: ignore
        text = ""
        with fitz.open(path) as doc:
            for p in doc:
                text += (p.get_text() or "") + "\n"
        if text.strip():
            return text
    except Exception:
        pass
    # Fallback: pdfminer.six if available
    try:
        from pdfminer.high_level import extract_text  # type: ignore
        text = extract_text(path) or ""
        if text.strip():
            return text
    except Exception:
        pass
    return ""


def _docx_to_text(path: str) -> str:
    try:
        import docx  # type: ignore
    except Exception:
        return ""
    try:
        d = docx.Document(path)
        lines = []
        for para in d.paragraphs:
            if para.text:
                lines.append(para.text)
        # tables
        for t in d.tables:
            for row in t.rows:
                cell_text = " | ".join([c.text.strip() for c in row.cells if c.text])
                if cell_text:
                    lines.append(cell_text)
        return "\n".join(lines)
    except Exception:
        return ""


def _ppt_to_text(path: str) -> str:
    # Support both .pptx (python-pptx) and legacy .ppt via fallback if possible
    suf = Path(path).suffix.lower()
    if suf == ".pptx":
        try:
            from pptx import Presentation  # type: ignore
        except Exception:
            return ""
        try:
            prs = Presentation(path)
            lines: List[str] = []
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "has_text_frame") and shape.has_text_frame:
                        for p in shape.text_frame.paragraphs:
                            txt = "".join(run.text for run in p.runs) or p.text
                            if txt:
                                lines.append(txt)
            return "\n".join(lines)
        except Exception:
            return ""
    else:
        # .ppt legacy: try using python-pptx won't work; if unoconv/libreoffice env not guaranteed, return empty
        return ""


def _read_file_text(path: str) -> str:
    p = Path(path)
    suf = p.suffix.lower()
    if suf in [".txt", ".md"]:
        return p.read_text(encoding="utf-8", errors="ignore")
    if suf in [".html", ".htm"]:
        return _html_to_text(p.read_text(encoding="utf-8", errors="ignore"))
    if suf == ".pdf":
        return _pdf_to_text(str(p))
    if suf == ".docx":
        return _docx_to_text(str(p))
    if suf in [".ppt", ".pptx"]:
        return _ppt_to_text(str(p))
    if suf == ".doc":
        # Try Apache Tika if available for legacy .doc
        try:
            from tika import parser  # type: ignore
            parsed = parser.from_file(str(p))
            return (parsed.get("content") or "").strip()
        except Exception:
            return ""
    return ""


def standardize_items(items: List[Dict]) -> List[Dict]:
    """
    输入 items，每项可包含：title、url、text、html、path
    输出标准文档：{title, url, content}
    - 支持解析类型：txt/md/html/htm/pdf/docx/ppt/pptx（doc 需 tika 可选）
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