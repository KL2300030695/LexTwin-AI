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


def test_changing_a_decision_preserves_the_previous_one_in_history():
    """A reviewer approves, then later spots an error and rejects instead --
    the original approval must not be silently erased."""
    entry = audit_service.create_entry(_sample_create())
    audit_service.record_decision(entry.id, AuditDecision.APPROVED, reviewer="alice@example.com")
    corrected = audit_service.record_decision(entry.id, AuditDecision.REJECTED, reviewer="bob@example.com")

    assert corrected.decision == AuditDecision.REJECTED
    assert corrected.reviewer == "bob@example.com"
    assert len(corrected.revision_history) == 1
    assert corrected.revision_history[0].decision == AuditDecision.APPROVED
    assert corrected.revision_history[0].reviewer == "alice@example.com"

    refetched = audit_service.get_entry(entry.id)
    assert len(refetched.revision_history) == 1


def test_changing_a_decision_multiple_times_accumulates_history_in_order():
    entry = audit_service.create_entry(_sample_create())
    audit_service.record_decision(entry.id, AuditDecision.APPROVED, reviewer="alice")
    audit_service.record_decision(entry.id, AuditDecision.REJECTED, reviewer="bob")
    final = audit_service.record_decision(entry.id, AuditDecision.APPROVED, reviewer="carol")

    assert final.decision == AuditDecision.APPROVED
    assert final.reviewer == "carol"
    assert [r.reviewer for r in final.revision_history] == ["alice", "bob"]


def test_first_decision_from_pending_does_not_create_a_history_entry():
    entry = audit_service.create_entry(_sample_create())
    decided = audit_service.record_decision(entry.id, AuditDecision.APPROVED, reviewer="alice")
    assert decided.revision_history == []
