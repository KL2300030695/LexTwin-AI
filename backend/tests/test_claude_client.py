import app.services.claude_client as claude_client
from app.services.claude_client import ClaudeClientError, check_contradiction

import pytest


def test_missing_api_key_raises_clear_error(monkeypatch):
    monkeypatch.setattr(claude_client.settings, "ANTHROPIC_API_KEY", "")
    monkeypatch.setattr(claude_client, "_client", None)

    with pytest.raises(ClaudeClientError, match="ANTHROPIC_API_KEY"):
        check_contradiction("Payment Terms", "5.1", "text a", "3.3", "text b")
