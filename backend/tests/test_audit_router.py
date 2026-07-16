from fastapi.testclient import TestClient

from app.auth import CurrentUser, Role, get_current_user
from app.main import app

client = TestClient(app)


def _as_reviewer():
    """conftest.py's autouse fixture defaults every test to 'admin'; this
    downgrades the test identity to verify the decision endpoint actually
    rejects a plain (but authenticated) reviewer, not just an
    unauthenticated caller."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(uid="reviewer-uid", email="r@example.com", role=Role.REVIEWER)

# Storage isolation (never touch real Firestore) is handled globally by
# tests/conftest.py's autouse _force_local_store fixture.


def _create_payload(**overrides):
    payload = {
        "msa_doc_id": "msa1",
        "sow_doc_id": "sow1",
        "doc_id": "sow1",
        "clause_id": "sow1::3.3",
        "topic": "Payment Terms",
        "original_text": "Pay within fifteen days.",
        "risk_rating": "contradiction",
        "ai_suggestion": "Pay within forty-five days.",
        "ai_rationale": "Aligned with the MSA.",
    }
    payload.update(overrides)
    return payload


def test_create_and_list_audit_entry():
    create_resp = client.post("/api/audit/entries", json=_create_payload())
    assert create_resp.status_code == 200
    entry = create_resp.json()
    assert entry["decision"] == "pending"

    list_resp = client.get("/api/audit/entries", params={"msa_doc_id": "msa1", "sow_doc_id": "sow1"})
    assert list_resp.status_code == 200
    entries = list_resp.json()
    assert any(e["id"] == entry["id"] for e in entries)


def test_decision_endpoint_approves_entry():
    """`reviewer` in the request body is no longer accepted -- who decided
    is derived server-side from the caller's verified identity (see
    conftest.py's _default_authenticated_user, which authenticates every
    router test as test@example.com)."""
    entry = client.post("/api/audit/entries", json=_create_payload()).json()

    decision_resp = client.post(
        f"/api/audit/entries/{entry['id']}/decision",
        json={"decision": "approved"},
    )
    assert decision_resp.status_code == 200
    body = decision_resp.json()
    assert body["decision"] == "approved"
    assert body["reviewer"] == "test@example.com"
    assert body["decided_at"] is not None


def test_decision_endpoint_allows_changing_an_already_decided_entry():
    entry = client.post("/api/audit/entries", json=_create_payload()).json()
    client.post(f"/api/audit/entries/{entry['id']}/decision", json={"decision": "approved"})

    response = client.post(
        f"/api/audit/entries/{entry['id']}/decision",
        json={"decision": "rejected"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "rejected"
    assert body["reviewer"] == "test@example.com"
    assert len(body["revision_history"]) == 1
    assert body["revision_history"][0]["decision"] == "approved"
    assert body["revision_history"][0]["reviewer"] == "test@example.com"


def test_decision_endpoint_404_for_missing_entry():
    response = client.post(
        "/api/audit/entries/audit-nope/decision",
        json={"decision": "rejected"},
    )
    assert response.status_code == 404


def test_list_filters_by_pair():
    client.post("/api/audit/entries", json=_create_payload(msa_doc_id="msaA", sow_doc_id="sowA"))
    client.post("/api/audit/entries", json=_create_payload(msa_doc_id="msaB", sow_doc_id="sowB"))

    resp = client.get("/api/audit/entries", params={"msa_doc_id": "msaA", "sow_doc_id": "sowA"})
    entries = resp.json()
    assert all(e["msa_doc_id"] == "msaA" for e in entries)


def test_reviewer_can_create_and_list_but_not_decide():
    """Creating/viewing audit entries is any-authenticated-role; recording a
    decision (the actual approve/reject authority) requires 'approver' or
    higher -- a plain reviewer is authenticated but not authorized for that
    specific action."""
    entry = client.post("/api/audit/entries", json=_create_payload()).json()

    _as_reviewer()
    create_resp = client.post("/api/audit/entries", json=_create_payload())
    assert create_resp.status_code == 200
    list_resp = client.get("/api/audit/entries")
    assert list_resp.status_code == 200

    decision_resp = client.post(f"/api/audit/entries/{entry['id']}/decision", json={"decision": "approved"})
    assert decision_resp.status_code == 403
