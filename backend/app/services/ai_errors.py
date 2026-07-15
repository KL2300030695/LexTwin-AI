"""Shared error type for the AI provider layer.

LocalLLMClientError and GeminiClientError both subclass this, so callers that
only care "did the AI call fail" (app/services/contradiction_service.py,
redline_service.py, chat_service.py) can catch this one type without
depending on which provider (local_llm_client.py or gemini_client.py) is
actually configured via settings.AI_PROVIDER.
"""
from __future__ import annotations


class AIClientError(RuntimeError):
    """Raised when the configured AI provider call fails after SDK-level
    retries, or when it isn't configured. Callers should treat this as
    'cannot evaluate right now', not as a crash."""
