from __future__ import annotations

from pathlib import Path

from app.models.schema import DocType, ParsedDocument
from app.parsers.docx_parser import parse_docx
from app.parsers.pdf_parser import parse_pdf


def parse_document(file_path: str, doc_id: str, filename: str, doc_type: DocType) -> ParsedDocument:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return parse_pdf(file_path, doc_id, filename, doc_type)
    if ext in (".docx", ".doc"):
        if ext == ".doc":
            raise ValueError("Legacy .doc format is not supported; please convert to .docx or .pdf.")
        return parse_docx(file_path, doc_id, filename, doc_type)
    raise ValueError(f"Unsupported file type: {ext}. Upload a .pdf or .docx file.")
