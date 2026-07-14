"""Tests the provider dispatcher (app/services/ai_client.py) routes to the
right provider module based on settings.AI_PROVIDER, and that both providers'
error types are catchable as the shared AIClientError -- what
contradiction_service.py and redline_service.py actually rely on."""
from unittest.mock import patch

import app.services.ai_client as ai_client
from app.services.ai_client import AIClientError
from app.services.ai_schemas import ContradictionJudgment, FallbackSuggestion
from app.services.claude_client import ClaudeClientError
from app.services.gemini_client import GeminiClientError


def test_defaults_to_claude(monkeypatch):
    monkeypatch.setattr(ai_client.settings, "AI_PROVIDER", "claude")
    fake = ContradictionJudgment(has_contradiction=True, explanation="conflict", confidence=0.9)
    with patch("app.services.claude_client.check_contradiction", return_value=fake) as mock_claude, \
         patch("app.services.gemini_client.check_contradiction") as mock_gemini:
        result = ai_client.check_contradiction("Payment Terms", "5.1", "a", "3.3", "b")

    assert result == fake
    mock_claude.assert_called_once_with("Payment Terms", "5.1", "a", "3.3", "b")
    mock_gemini.assert_not_called()


def test_gemini_provider_routes_to_gemini_client(monkeypatch):
    monkeypatch.setattr(ai_client.settings, "AI_PROVIDER", "gemini")
    fake = ContradictionJudgment(has_contradiction=False, explanation="no conflict", confidence=0.8)
    with patch("app.services.gemini_client.check_contradiction", return_value=fake) as mock_gemini, \
         patch("app.services.claude_client.check_contradiction") as mock_claude:
        result = ai_client.check_contradiction("Payment Terms", "5.1", "a", "3.3", "b")

    assert result == fake
    mock_gemini.assert_called_once_with("Payment Terms", "5.1", "a", "3.3", "b")
    mock_claude.assert_not_called()


def test_generate_fallback_language_routes_by_provider(monkeypatch):
    monkeypatch.setattr(ai_client.settings, "AI_PROVIDER", "gemini")
    fake = FallbackSuggestion(suggested_text="revised", rationale="why")
    with patch("app.services.gemini_client.generate_fallback_language", return_value=fake) as mock_gemini:
        result = ai_client.generate_fallback_language("heading", "text", "risk", None, None)

    assert result == fake
    mock_gemini.assert_called_once_with("heading", "text", "risk", None, None)


def test_claude_client_error_is_an_ai_client_error():
    assert issubclass(ClaudeClientError, AIClientError)


def test_gemini_client_error_is_an_ai_client_error():
    assert issubclass(GeminiClientError, AIClientError)
