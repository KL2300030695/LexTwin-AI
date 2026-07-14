from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.audit import AuditDecisionUpdate, AuditEntry, AuditEntryCreate
from app.services import audit_service

router = APIRouter()


@router.post("/entries", response_model=AuditEntry)
def create(payload: AuditEntryCreate):
    return audit_service.create_entry(payload)


@router.get("/entries", response_model=list[AuditEntry])
def list_all(msa_doc_id: str | None = None, sow_doc_id: str | None = None):
    return audit_service.list_entries(msa_doc_id, sow_doc_id)


@router.post("/entries/{entry_id}/decision", response_model=AuditEntry)
def decide(entry_id: str, payload: AuditDecisionUpdate):
    try:
        return audit_service.record_decision(entry_id, payload.decision, payload.reviewer)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
