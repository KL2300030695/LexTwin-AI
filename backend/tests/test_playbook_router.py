from fastapi.testclient import TestClient

from app.auth import CurrentUser, Role, get_current_user
from app.main import app

client = TestClient(app)


def _as_reviewer():
    """Temporarily downgrades the test identity to 'reviewer' (conftest.py's
    autouse fixture defaults every test to 'admin') to verify admin-only
    routes actually reject a lower-privileged, but still authenticated,
    caller -- not just an unauthenticated one."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(uid="reviewer-uid", email="r@example.com", role=Role.REVIEWER)


def test_get_topics_returns_defaults():
    response = client.get("/api/playbook/topics")
    assert response.status_code == 200
    topics = response.json()
    assert any(t["topic"] == "Payment Terms" for t in topics)


def test_put_topics_replaces_config():
    response = client.put(
        "/api/playbook/topics",
        json={"topics": [{"topic": "Custom Topic", "patterns": [r"\bcustom\b"]}]},
    )
    assert response.status_code == 200
    assert response.json() == [{"topic": "Custom Topic", "patterns": [r"\bcustom\b"]}]

    refetch = client.get("/api/playbook/topics").json()
    assert refetch == [{"topic": "Custom Topic", "patterns": [r"\bcustom\b"]}]


def test_reset_topics_restores_defaults():
    client.put("/api/playbook/topics", json={"topics": [{"topic": "Custom Topic", "patterns": []}]})
    response = client.post("/api/playbook/topics/reset")
    assert response.status_code == 200
    topics = response.json()
    assert any(t["topic"] == "Payment Terms" for t in topics)
    assert not any(t["topic"] == "Custom Topic" for t in topics)


def test_get_reference_categories_pools_all_sources():
    response = client.get("/api/playbook/categories")
    assert response.status_code == 200
    categories = response.json()
    assert all("source" in c for c in categories)
    assert any(c["source"] == "CUAD v1" and c["category"] == "Governing Law" for c in categories)


def test_reviewer_cannot_edit_topics():
    """Editing the shared Playbook config is admin-only -- a reviewer is
    authenticated (not a 401 case) but not authorized for this specific
    action (403)."""
    _as_reviewer()
    response = client.put(
        "/api/playbook/topics",
        json={"topics": [{"topic": "Custom Topic", "patterns": [r"\bcustom\b"]}]},
    )
    assert response.status_code == 403


def test_reviewer_cannot_reset_topics():
    _as_reviewer()
    response = client.post("/api/playbook/topics/reset")
    assert response.status_code == 403


def test_reviewer_can_still_read_topics():
    """Reading the config is fine for any authenticated role -- only
    mutating it is admin-gated."""
    _as_reviewer()
    response = client.get("/api/playbook/topics")
    assert response.status_code == 200
