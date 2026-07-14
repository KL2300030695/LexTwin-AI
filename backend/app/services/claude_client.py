"""Thin wrapper around the Claude API for the genuinely LLM-shaped parts of
this app: judging whether two same-topic clauses conflict (Phase 5), and
drafting fallback replacement language for a flagged clause (Phase 6).

Everything else (topic alignment, missing-reference gating, the word-level
diff itself) is deterministic and lives elsewhere -- this module is
intentionally small and isolated so it's easy to mock in tests without
hitting the network.

The system prompts and response schemas live in app/services/ai_schemas.py,
shared with app/services/gemini_client.py, so switching AI_PROVIDER never
changes what's being asked -- only the transport does. ContradictionJudgment
and FallbackSuggestion are re-exported here for backward compatibility (existing
tests and callers import them from this module).
"""
from __future__ import annotations

import anthropic

from app.config import settings
from app.services.ai_errors import AIClientError
from app.services.ai_schemas import (
    CHAT_SYSTEM_PROMPT,
    CONTRADICTION_SYSTEM_PROMPT,
    FALLBACK_SYSTEM_PROMPT,
    ChatAnswer,
    ContradictionJudgment,
    FallbackSuggestion,
    chat_user_content,
    contradiction_user_content,
    fallback_user_content,
)

__all__ = [
    "ClaudeClientError",
    "ContradictionJudgment",
    "FallbackSuggestion",
    "ChatAnswer",
    "check_contradiction",
    "generate_fallback_language",
    "answer_chat_question",
]


class ClaudeClientError(AIClientError):
    """Raised when the Claude API call fails after SDK-level retries, or when
    no API key is configured."""


_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not settings.ANTHROPIC_API_KEY:
            raise ClaudeClientError(
                "ANTHROPIC_API_KEY is not configured; cannot run AI-assisted analysis."
            )
        _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


def check_contradiction(
    topic: str, msa_heading: str, msa_text: str, sow_heading: str, sow_text: str
) -> ContradictionJudgment:
    """Sends one MSA/SOW clause pair to Claude and returns a structured
    judgment. The anthropic SDK already retries connection errors, 429s, and
    5xxs with backoff (default max_retries=2); we only need to translate a
    still-failing call into our own error type."""
    client = _get_client()
    user_content = contradiction_user_content(topic, msa_heading, msa_text, sow_heading, sow_text)
    try:
        response = client.messages.parse(
            model=settings.CLAUDE_MODEL,
            max_tokens=1024,
            system=CONTRADICTION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
            output_format=ContradictionJudgment,
        )
    except anthropic.APIError as e:
        raise ClaudeClientError(f"Claude API call failed: {e}") from e

    if response.parsed_output is None:
        raise ClaudeClientError("Claude response did not match the expected schema.")
    return response.parsed_output


def answer_chat_question(context_block: str, history_block: str, question: str) -> ChatAnswer:
    """Answers a Chat with Contract question grounded in already-retrieved
    clause context (app/rag/, app/services/chat_service.py) -- this
    function does no retrieval itself, it only synthesizes an answer."""
    client = _get_client()
    user_content = chat_user_content(context_block, history_block, question)
    try:
        response = client.messages.parse(
            model=settings.CLAUDE_MODEL,
            max_tokens=1024,
            system=CHAT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
            output_format=ChatAnswer,
        )
    except anthropic.APIError as e:
        raise ClaudeClientError(f"Claude API call failed: {e}") from e

    if response.parsed_output is None:
        raise ClaudeClientError("Claude response did not match the expected schema.")
    return response.parsed_output


def generate_fallback_language(
    original_heading: str, original_text: str, risk_reason: str, reference_heading: str | None, reference_text: str | None
) -> FallbackSuggestion:
    """Drafts fallback replacement text for a single flagged clause."""
    client = _get_client()
    user_content = fallback_user_content(original_heading, original_text, risk_reason, reference_heading, reference_text)

    try:
        response = client.messages.parse(
            model=settings.CLAUDE_MODEL,
            max_tokens=1024,
            system=FALLBACK_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
            output_format=FallbackSuggestion,
        )
    except anthropic.APIError as e:
        raise ClaudeClientError(f"Claude API call failed: {e}") from e

    if response.parsed_output is None:
        raise ClaudeClientError("Claude response did not match the expected schema.")
    return response.parsed_output
