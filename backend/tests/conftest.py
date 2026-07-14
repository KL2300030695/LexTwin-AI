import pytest

import app.firebase as firebase_module


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
