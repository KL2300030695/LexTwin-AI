import pytest

import app.firebase as firebase_module
from app.auth import CurrentUser, Role, get_current_user
from app.main import app


@pytest.fixture(autouse=True)
def _default_authenticated_user():
    """Router tests hit the app via FastAPI's TestClient(app) directly and
    don't carry a real Firebase ID token -- every route now requires
    get_current_user, so without this override every router test would 401.
    Defaults every test to an authenticated admin (the highest-privilege
    role) so all tests written before auth existed keep passing unmodified.
    A test that specifically wants to verify role-gating (403 for a
    reviewer hitting an approver/admin-only route, 401 for no override at
    all) re-overrides this dependency again within its own test body."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        uid="test-uid", email="test@example.com", role=Role.ADMIN
    )
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(autouse=True)
def _force_local_store(tmp_path, monkeypatch):
    """Global safety net: every test runs against an isolated local JSON
    store in a throwaway tmp_path, regardless of the real .env's
    USE_FIREBASE setting. Without this, a test that calls get_store()
    directly (or transitively, e.g. via the playbook/topic-rules config)
    would silently read from and write to a real Firestore project --
    this happened once already with the audit trail tests, which leaked
    entries into production Firestore before per-file fixtures were added.
    A global fixture means every future feature gets this for free."""
    monkeypatch.setattr(firebase_module, "_store", None)
    monkeypatch.setattr(firebase_module.settings, "USE_FIREBASE", False)
    monkeypatch.setattr(firebase_module.settings, "LOCAL_DATA_DIR", tmp_path)
    yield
    monkeypatch.setattr(firebase_module, "_store", None)
