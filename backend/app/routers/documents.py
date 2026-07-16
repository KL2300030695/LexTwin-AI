from __future__ import annotations

import shutil
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi import Form

from app.models.schema import DocType, ParsedDocument
from app.services.document_service import UPLOADS_TMP_DIR, get_document, ingest_document, list_documents, replace_document

router = APIRouter()


@router.post("/upload", response_model=ParsedDocument)
async def upload_document(file: UploadFile = File(...), doc_type: DocType = Form(...)):
    suffix = "".join(ch for ch in (file.filename or "") if ch.isalnum() or ch in "._-")
    tmp_path = UPLOADS_TMP_DIR / f"{uuid.uuid4().hex}_{suffix}"
    with tmp_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        parsed = ingest_document(str(tmp_path), file.filename or suffix, doc_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        tmp_path.unlink(missing_ok=True)

    return parsed


@router.put("/{doc_id}/replace", response_model=ParsedDocument)
async def replace_document_by_id(doc_id: str, file: UploadFile = File(...)):
    """Re-uploads an amended version of a document already in the system,
    keeping the same doc_id instead of creating an unrelated duplicate --
    see app.services.document_service.replace_document for what this does
    and does not carry forward (audit trail entries are not migrated)."""
    existing = get_document(doc_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Document not found")

    suffix = "".join(ch for ch in (file.filename or "") if ch.isalnum() or ch in "._-")
    tmp_path = UPLOADS_TMP_DIR / f"{uuid.uuid4().hex}_{suffix}"
    with tmp_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        parsed = replace_document(doc_id, str(tmp_path), file.filename or suffix, existing.doc_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        tmp_path.unlink(missing_ok=True)

    return parsed


@router.get("/{doc_id}", response_model=ParsedDocument)
def get_document_by_id(doc_id: str):
    doc = get_document(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("", response_model=list[ParsedDocument])
def list_all_documents():
    return list_documents()
