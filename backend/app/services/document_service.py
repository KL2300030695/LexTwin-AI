from __future__ import annotations

import uuid
from pathlib import Path

from app.config import settings
from app.firebase import get_store
from app.models.schema import DocType, ParsedDocument
from app.parsers import parse_document

DOCUMENTS_COLLECTION = "documents"
UPLOADS_TMP_DIR = settings.LOCAL_DATA_DIR / "uploads"
UPLOADS_TMP_DIR.mkdir(parents=True, exist_ok=True)


def ingest_document(local_file_path: str, original_filename: str, doc_type: DocType) -> ParsedDocument:
    """Parses an already-saved-to-disk upload and persists the parsed structure."""
    doc_id = f"{doc_type.value.lower()}-{uuid.uuid4().hex[:8]}"
    parsed = parse_document(local_file_path, doc_id, original_filename, doc_type)

    store = get_store()
    store.save_file(f"{doc_id}/{original_filename}", local_file_path)
    store.save(DOCUMENTS_COLLECTION, doc_id, parsed.model_dump(mode="json"))
    return parsed


def get_document(doc_id: str) -> ParsedDocument | None:
    store = get_store()
    data = store.get(DOCUMENTS_COLLECTION, doc_id)
    if data is None:
        return None
    return ParsedDocument.model_validate(data)


def list_documents() -> list[ParsedDocument]:
    store = get_store()
    return [get_document(doc_id) for doc_id in store.list_ids(DOCUMENTS_COLLECTION)]
