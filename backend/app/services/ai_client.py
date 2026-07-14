"""Provider dispatcher: routes to app/services/claude_client.py or
app/services/gemini_client.py based on settings.AI_PROVIDER. This is the
only module app/services/contradiction_service.py and
app/services/redline_service.py import from -- neither needs to know which
provider is active. Both providers ask the exact same question against the
exact same schema (app/services/ai_schemas.py); only the transport differs.
"""
from __future__ import annotations

from app.config import settings
from app.services.ai_errors import AIClientError
from app.services.ai_schemas import ChatAnswer, ContradictionJudgment, FallbackSuggestion

__all__ = ["AIClientError", "check_contradiction", "generate_fallback_language", "answer_chat_question"]


def check_contradiction(
    topic: str, msa_heading: str, msa_text: str, sow_heading: str, sow_text: str
) -> ContradictionJudgment:
    if settings.AI_PROVIDER == "gemini":
        from app.services import gemini_client

        return gemini_client.check_contradiction(topic, msa_heading, msa_text, sow_heading, sow_text)

    from app.services import claude_client

    return claude_client.check_contradiction(topic, msa_heading, msa_text, sow_heading, sow_text)


def generate_fallback_language(
    original_heading: str, original_text: str, risk_reason: str, reference_heading: str | None, reference_text: str | None
) -> FallbackSuggestion:
    if settings.AI_PROVIDER == "gemini":
        from app.services import gemini_client

        return gemini_client.generate_fallback_language(
            original_heading, original_text, risk_reason, reference_heading, reference_text
        )

    from app.services import claude_client

    return claude_client.generate_fallback_language(
        original_heading, original_text, risk_reason, reference_heading, reference_text
    )


def answer_chat_question(context_block: str, history_block: str, question: str) -> ChatAnswer:
    if settings.AI_PROVIDER == "gemini":
        from app.services import gemini_client

        return gemini_client.answer_chat_question(context_block, history_block, question)

    from app.services import claude_client

    return claude_client.answer_chat_question(context_block, history_block, question)
