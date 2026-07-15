"""Thin wrapper around the Gemini API, mirroring app/services/local_llm_client.py's
function signatures exactly -- same three functions, same structured-output
contract (app/services/ai_schemas.py). Selected instead of the local model
when AI_PROVIDER=gemini (see app/services/ai_client.py); the rest of the app
never imports this module directly.

This is an OPT-IN alternative, not a hidden default: AI_PROVIDER defaults to
"local" (see app/config.py), and this module raises immediately if no
GEMINI_API_KEY is configured rather than silently falling back to it.
"""
from __future__ import annotations

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types

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
    "GeminiClientError",
    "check_contradiction",
    "generate_fallback_language",
    "answer_chat_question",
]


class GeminiClientError(AIClientError):
    """Raised when the Gemini API call fails after SDK-level retries, or when
    no API key is configured."""


_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not settings.GEMINI_API_KEY:
            raise GeminiClientError(
                "GEMINI_API_KEY is not configured; cannot run AI-assisted analysis via Gemini."
            )
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def check_contradiction(
    topic: str, msa_heading: str, msa_text: str, sow_heading: str, sow_text: str
) -> ContradictionJudgment:
    """Sends one MSA/SOW clause pair to Gemini and returns a structured
    judgment -- same prompt and schema as the local-model path."""
    client = _get_client()
    user_content = contradiction_user_content(topic, msa_heading, msa_text, sow_heading, sow_text)
    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=user_content,
            config=genai_types.GenerateContentConfig(
                system_instruction=CONTRADICTION_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=ContradictionJudgment,
            ),
        )
    except genai_errors.APIError as e:
        raise GeminiClientError(f"Gemini API call failed: {e}") from e

    if not isinstance(response.parsed, ContradictionJudgment):
        raise GeminiClientError("Gemini response did not match the expected schema.")
    return response.parsed


def answer_chat_question(context_block: str, history_block: str, question: str) -> ChatAnswer:
    """Answers a Chat with Contract question grounded in already-retrieved
    clause context -- same prompt and schema as the local-model path. Does no
    retrieval itself, only answer synthesis."""
    client = _get_client()
    user_content = chat_user_content(context_block, history_block, question)
    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=user_content,
            config=genai_types.GenerateContentConfig(
                system_instruction=CHAT_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=ChatAnswer,
            ),
        )
    except genai_errors.APIError as e:
        raise GeminiClientError(f"Gemini API call failed: {e}") from e

    if not isinstance(response.parsed, ChatAnswer):
        raise GeminiClientError("Gemini response did not match the expected schema.")
    return response.parsed


def generate_fallback_language(
    original_heading: str, original_text: str, risk_reason: str, reference_heading: str | None, reference_text: str | None
) -> FallbackSuggestion:
    """Drafts fallback replacement text for a single flagged clause -- same
    prompt and schema as the local-model path."""
    client = _get_client()
    user_content = fallback_user_content(original_heading, original_text, risk_reason, reference_heading, reference_text)

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=user_content,
            config=genai_types.GenerateContentConfig(
                system_instruction=FALLBACK_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=FallbackSuggestion,
            ),
        )
    except genai_errors.APIError as e:
        raise GeminiClientError(f"Gemini API call failed: {e}") from e

    if not isinstance(response.parsed, FallbackSuggestion):
        raise GeminiClientError("Gemini response did not match the expected schema.")
    return response.parsed
