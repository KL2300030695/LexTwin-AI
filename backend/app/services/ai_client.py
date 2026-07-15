"""Provider dispatcher: routes to app/services/local_llm_client.py (default)
or app/services/gemini_client.py based on settings.AI_PROVIDER. This is the
only module app/services/contradiction_service.py, redline_service.py, and
chat_service.py import AI functionality from -- none of them need to know
which provider is active. Both providers are asked the exact same question
against the exact same schema (app/services/ai_schemas.py); only the
transport differs.
"""
from __future__ import annotations

from app.config import settings
from app.services.ai_errors import AIClientError
from app.services.ai_schemas import ChatAnswer, ContradictionJudgment, FallbackSuggestion

__all__ = [
    "AIClientError",
    "ContradictionJudgment",
    "FallbackSuggestion",
    "ChatAnswer",
    "check_contradiction",
    "generate_fallback_language",
    "answer_chat_question",
]


def check_contradiction(
    topic: str, msa_heading: str, msa_text: str, sow_heading: str, sow_text: str
) -> ContradictionJudgment:
    if settings.AI_PROVIDER == "gemini":
        from app.services import gemini_client

        return gemini_client.check_contradiction(topic, msa_heading, msa_text, sow_heading, sow_text)

    from app.services import local_llm_client

    return local_llm_client.check_contradiction(topic, msa_heading, msa_text, sow_heading, sow_text)


def generate_fallback_language(
    original_heading: str, original_text: str, risk_reason: str, reference_heading: str | None, reference_text: str | None
) -> FallbackSuggestion:
    if settings.AI_PROVIDER == "gemini":
        from app.services import gemini_client

        return gemini_client.generate_fallback_language(
            original_heading, original_text, risk_reason, reference_heading, reference_text
        )

    from app.services import local_llm_client

    return local_llm_client.generate_fallback_language(
        original_heading, original_text, risk_reason, reference_heading, reference_text
    )


def answer_chat_question(context_block: str, history_block: str, question: str) -> ChatAnswer:
    if settings.AI_PROVIDER == "gemini":
        from app.services import gemini_client

        return gemini_client.answer_chat_question(context_block, history_block, question)

    from app.services import local_llm_client

    return local_llm_client.answer_chat_question(context_block, history_block, question)
