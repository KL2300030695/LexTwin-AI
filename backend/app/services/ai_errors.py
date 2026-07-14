"""Shared error type for both AI providers (Claude, Gemini).

ClaudeClientError and GeminiClientError both subclass this, so callers that
only care "did the configured AI provider fail" (app/services/contradiction_service.py,
app/services/redline_service.py) can catch one type regardless of which
provider is active, while code that cares about a specific provider can still
catch the narrower subclass.
"""
from __future__ import annotations


class AIClientError(RuntimeError):
    """Raised when the configured AI provider call fails after SDK-level
    retries, or when it isn't configured. Callers should treat this as
    'cannot evaluate right now', not as a crash."""
