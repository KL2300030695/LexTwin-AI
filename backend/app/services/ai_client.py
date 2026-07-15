"""Single entry point the rest of the app imports AI functionality from --
app/services/contradiction_service.py, redline_service.py, and
chat_service.py all import check_contradiction/generate_fallback_language/
answer_chat_question from here, not from local_llm_client.py directly. Kept
as a thin re-export (rather than inlining local_llm_client's functions
directly into those call sites) so a different local model, or a hosted
provider, can be swapped in later without touching the three services that
consume this module.
"""
from __future__ import annotations

from app.services.ai_errors import AIClientError
from app.services.local_llm_client import (
    ChatAnswer,
    ContradictionJudgment,
    FallbackSuggestion,
    answer_chat_question,
    check_contradiction,
    generate_fallback_language,
)

__all__ = [
    "AIClientError",
    "ContradictionJudgment",
    "FallbackSuggestion",
    "ChatAnswer",
    "check_contradiction",
    "generate_fallback_language",
    "answer_chat_question",
]
