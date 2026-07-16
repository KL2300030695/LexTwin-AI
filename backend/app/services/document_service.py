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


def _parse_and_store(doc_id: str, local_file_path: str, original_filename: str, doc_type: DocType) -> ParsedDocument:
    parsed = parse_document(local_file_path, doc_id, original_filename, doc_type)
    store = get_store()
    store.save_file(f"{doc_id}/{original_filename}", local_file_path)
    store.save(DOCUMENTS_COLLECTION, doc_id, parsed.model_dump(mode="json"))
    return parsed


def ingest_document(local_file_path: str, original_filename: str, doc_type: DocType) -> ParsedDocument:
    """Parses an already-saved-to-disk upload and persists it under a brand-new doc_id."""
    doc_id = f"{doc_type.value.lower()}-{uuid.uuid4().hex[:8]}"
    return _parse_and_store(doc_id, local_file_path, original_filename, doc_type)


def replace_document(doc_id: str, local_file_path: str, original_filename: str, doc_type: DocType) -> ParsedDocument:
    """Re-parses a new file into an EXISTING doc_id, overwriting its stored
    content in place -- for re-uploading an amended MSA/SOW without piling up
    an unrelated duplicate doc_id the reviewer has to remember to pick over
    the stale one (see README Roadmap: no versioning yet, this is the
    minimal "replace in place" step short of full version history).
    Audit trail entries and risk analyses computed against the old content
    are not migrated -- they still reference this doc_id, but may cite
    clause_ids that no longer exist if the clause structure changed."""
    return _parse_and_store(doc_id, local_file_path, original_filename, doc_type)


def get_document(doc_id: str) -> ParsedDocument | None:
    store = get_store()
    data = store.get(DOCUMENTS_COLLECTION, doc_id)
    if data is None:
        return None
    return ParsedDocument.model_validate(data)


def list_documents() -> list[ParsedDocument]:
    store = get_store()
    return [get_document(doc_id) for doc_id in store.list_ids(DOCUMENTS_COLLECTION)]
