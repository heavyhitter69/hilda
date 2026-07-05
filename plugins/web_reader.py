"""
plugins/web_reader.py — Document reading and Q&A for Hilda.

Reads local files (PDF, DOCX, TXT, CSV) and provides LLM-powered
summarization and question-answering over document contents.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from config.settings import settings
from core.logger import get_logger

log = get_logger(__name__)


def read_document(path: str, max_chars: int = 5000) -> str:
    """
    Read a local document and return its text content.
    Supports: PDF, DOCX, TXT, CSV, MD, JSON, PY, JS, and other text files.
    """
    p = Path(path).expanduser()
    if not p.exists():
        return f"File not found: {path}"

    ext = p.suffix.lower()

    try:
        # PDF
        if ext == ".pdf":
            return _read_pdf(p, max_chars)

        # DOCX
        if ext == ".docx":
            return _read_docx(p, max_chars)

        # Text-based files
        if ext in (".txt", ".md", ".csv", ".json", ".py", ".js", ".ts",
                    ".html", ".css", ".xml", ".yml", ".yaml", ".ini",
                    ".cfg", ".log", ".sql", ".sh", ".bat", ".ps1"):
            return _read_text(p, max_chars)

        # Try as text anyway
        return _read_text(p, max_chars)

    except Exception as e:
        log.error("Failed to read %s: %s", path, e)
        return f"Could not read file: {e}"


def _read_pdf(path: Path, max_chars: int) -> str:
    """Extract text from a PDF file."""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(str(path))
        text_parts = []
        for page in reader.pages:
            text = page.extract_text() or ""
            text_parts.append(text)
            if sum(len(t) for t in text_parts) > max_chars:
                break
        result = "\n\n".join(text_parts)
        return result[:max_chars]
    except ImportError:
        log.warning("PyPDF2 not installed — cannot read PDF files.")
        return "PDF reading requires PyPDF2. Install with: pip install PyPDF2"
    except Exception as e:
        return f"PDF read error: {e}"


def _read_docx(path: Path, max_chars: int) -> str:
    """Extract text from a DOCX file."""
    try:
        from docx import Document
        doc = Document(str(path))
        text_parts = [para.text for para in doc.paragraphs if para.text.strip()]
        result = "\n\n".join(text_parts)
        return result[:max_chars]
    except ImportError:
        log.warning("python-docx not installed — cannot read DOCX files.")
        return "DOCX reading requires python-docx. Install with: pip install python-docx"
    except Exception as e:
        return f"DOCX read error: {e}"


def _read_text(path: Path, max_chars: int) -> str:
    """Read a text-based file."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        return text[:max_chars]
    except Exception as e:
        return f"Text read error: {e}"


def summarize_document(path: str, question: Optional[str] = None) -> str:
    """
    Read a document and summarize it, or answer a specific question about it.
    """
    content = read_document(path, max_chars=5000)
    if content.startswith("File not found") or content.startswith("Could not"):
        return content

    filename = Path(path).name

    prompt = f"Document: {filename}\n\nContent:\n{content}\n\n"
    if question:
        prompt += f"Answer this question about the document: {question}"
    else:
        prompt += "Provide a concise summary of this document's key points."

    try:
        import ollama
        response = ollama.chat(
            model=settings.OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": "You summarize and analyze documents accurately. Be concise and highlight key points."},
                {"role": "user", "content": prompt},
            ],
            options={"temperature": 0.2, "num_predict": 500},
        )
        answer = response["message"]["content"].strip()
        log.info("Document summary generated for: %s", filename)
        return answer
    except Exception as e:
        log.error("Document summarization failed: %s", e)
        return f"Summary of {filename}:\n{content[:300]}..."
