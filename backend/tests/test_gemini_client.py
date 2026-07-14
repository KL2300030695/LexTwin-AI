import app.services.gemini_client as gemini_client
from app.services.gemini_client import GeminiClientError, check_contradiction

import pytest


def test_missing_api_key_raises_clear_error(monkeypatch):
    monkeypatch.setattr(gemini_client.settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(gemini_client, "_client", None)

    with pytest.raises(GeminiClientError, match="GEMINI_API_KEY"):
        check_contradiction("Payment Terms", "5.1", "text a", "3.3", "text b")
