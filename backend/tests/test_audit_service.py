from app.models.audit import AuditDecision, AuditEntryCreate
from app.services import audit_service

# Storage isolation (never touch real Firestore) is handled globally by
# tests/conftest.py's autouse _force_local_store fixture.


def _sample_create(msa_doc_id="msa1", sow_doc_id="sow1", clause_id="sow1::3.3") -> AuditEntryCreate:
    return AuditEntryCreate(
        msa_doc_id=msa_doc_id,
        sow_doc_id=sow_doc_id,
        doc_id=sow_doc_id,
        clause_id=clause_id,
        topic="Payment Terms",
        original_text="Client shall pay within fifteen days.",
        risk_rating="contradiction",
        ai_suggestion="Client shall pay within forty-five days.",
        ai_rationale="Aligned with the governing MSA.",
    )


def test_create_entry_defaults_to_pending():
    entry = audit_service.create_entry(_sample_create())
    assert entry.decision == AuditDecision.PENDING
    assert entry.decided_at is None
    assert entry.id.startswith("audit-")
    assert entry.created_at

    audit_service.get_entry(entry.id)  # doesn't raise


def test_get_entry_roundtrip():
    created = audit_service.create_entry(_sample_create())
    fetched = audit_service.get_entry(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.original_text == created.original_text


def test_get_entry_missing_returns_none():
    assert audit_service.get_entry("audit-does-not-exist") is None


def test_list_entries_filters_by_doc_pair():
    e1 = audit_service.create_entry(_sample_create(msa_doc_id="msaA", sow_doc_id="sowA"))
    e2 = audit_service.create_entry(_sample_create(msa_doc_id="msaB", sow_doc_id="sowB"))

    only_a = audit_service.list_entries(msa_doc_id="msaA", sow_doc_id="sowA")
    ids = {e.id for e in only_a}
    assert e1.id in ids
    assert e2.id not in ids


def test_record_decision_updates_status_and_timestamp():
    entry = audit_service.create_entry(_sample_create())
    decided = audit_service.record_decision(entry.id, AuditDecision.APPROVED, reviewer="alice@example.com")

    assert decided.decision == AuditDecision.APPROVED
    assert decided.reviewer == "alice@example.com"
    assert decided.decided_at is not None

    refetched = audit_service.get_entry(entry.id)
    assert refetched.decision == AuditDecision.APPROVED


def test_record_decision_missing_entry_raises():
    import pytest
    with pytest.raises(ValueError, match="not found"):
        audit_service.record_decision("audit-nope", AuditDecision.REJECTED, None)
