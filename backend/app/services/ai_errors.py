"""Shared error type for the local LLM client.

LocalLLMClientError subclasses this, so callers that only care "did the AI
call fail" (app/services/contradiction_service.py, redline_service.py,
chat_service.py) can catch this one type without depending on
local_llm_client.py directly.
"""
from __future__ import annotations


class AIClientError(RuntimeError):
    """Raised when the configured AI provider call fails after SDK-level
    retries, or when it isn't configured. Callers should treat this as
    'cannot evaluate right now', not as a crash."""
