from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth import CurrentUser, Role, get_current_user, require_role
from app.models.audit import AuditDecisionUpdate, AuditEntry, AuditEntryCreate
from app.services import audit_service

router = APIRouter()


@router.post("/entries", response_model=AuditEntry)
def create(payload: AuditEntryCreate, _: CurrentUser = Depends(get_current_user)):
    return audit_service.create_entry(payload)


@router.get("/entries", response_model=list[AuditEntry])
def list_all(
    msa_doc_id: str | None = None,
    sow_doc_id: str | None = None,
    _: CurrentUser = Depends(get_current_user),
):
    return audit_service.list_entries(msa_doc_id, sow_doc_id)


@router.post("/entries/{entry_id}/decision", response_model=AuditEntry)
def decide(
    entry_id: str,
    payload: AuditDecisionUpdate,
    user: CurrentUser = Depends(require_role(Role.APPROVER)),
):
    """Recording approve/reject is the one action the audit trail exists to
    protect, so it requires the 'approver' role (or admin) -- a plain
    reviewer can create entries and view them, but not decide them. The
    reviewer name recorded is the caller's own verified email, never a
    client-supplied string (see AuditDecisionUpdate)."""
    try:
        return audit_service.record_decision(entry_id, payload.decision, user.email or user.uid)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
