from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.firebase import get_store
from app.models.audit import AuditDecision, AuditEntry, AuditEntryCreate, AuditRevision

AUDIT_COLLECTION = "audit_trail"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_entry(payload: AuditEntryCreate) -> AuditEntry:
    entry = AuditEntry(
        id=f"audit-{uuid.uuid4().hex[:12]}",
        created_at=_now_iso(),
        **payload.model_dump(),
    )
    store = get_store()
    store.save(AUDIT_COLLECTION, entry.id, entry.model_dump(mode="json"))
    return entry


def get_entry(entry_id: str) -> AuditEntry | None:
    store = get_store()
    data = store.get(AUDIT_COLLECTION, entry_id)
    if data is None:
        return None
    return AuditEntry.model_validate(data)


def list_entries(msa_doc_id: str | None = None, sow_doc_id: str | None = None) -> list[AuditEntry]:
    store = get_store()
    entries = [get_entry(entry_id) for entry_id in store.list_ids(AUDIT_COLLECTION)]
    entries = [e for e in entries if e is not None]
    if msa_doc_id:
        entries = [e for e in entries if e.msa_doc_id == msa_doc_id]
    if sow_doc_id:
        entries = [e for e in entries if e.sow_doc_id == sow_doc_id]
    entries.sort(key=lambda e: e.created_at)
    return entries


def record_decision(entry_id: str, decision: AuditDecision, reviewer: str | None) -> AuditEntry:
    """Records a reviewer decision. If this entry already had a decision
    (a reviewer is correcting an earlier approve/reject after spotting an
    error), the previous decision is preserved in revision_history rather
    than silently overwritten -- the correction itself becomes part of the
    audit trail, not an erasure of what came before."""
    entry = get_entry(entry_id)
    if entry is None:
        raise ValueError(f"Audit entry not found: {entry_id}")
    if entry.decision != AuditDecision.PENDING:
        entry.revision_history.append(
            AuditRevision(decision=entry.decision, reviewer=entry.reviewer, decided_at=entry.decided_at)
        )
    entry.decision = decision
    entry.reviewer = reviewer
    entry.decided_at = _now_iso()
    store = get_store()
    store.save(AUDIT_COLLECTION, entry.id, entry.model_dump(mode="json"))
    return entry
