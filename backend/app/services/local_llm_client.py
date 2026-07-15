"""Local LLM client -- runs entirely on-machine via llama-cpp-python and a
downloaded GGUF model. No API key, no external network call at inference
time (only the one-time model download), no per-call cost, no rate limit.

Replaces the earlier Claude/Gemini hosted-provider setup. Structured output
is enforced by grammar-constrained decoding: the JSON Schema for each
response model (app/services/ai_schemas.py) is converted to a GBNF grammar
that the model's token sampling is constrained to follow, guaranteeing
syntactically valid JSON matching the expected shape. Verified directly that
this constrains *shape* (valid JSON, required fields, correct types) but not
numeric-range semantics like "confidence must be 0.0-1.0" -- see the
field_validator on ContradictionJudgment.confidence for how that's handled.

FastAPI runs sync endpoints in a thread pool, so concurrent requests can
reach this module concurrently. The underlying llama.cpp context (wrapped by
the single `Llama` instance below) is not safe for concurrent generation
calls from multiple threads -- verified directly: two concurrent inference
calls reproducibly crashed the whole process (a silent native crash, no
Python traceback), not just this request. `_llm_lock` serializes both model
loading and every inference call through the shared instance.
"""
from __future__ import annotations

import threading

from llama_cpp import Llama

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
    "LocalLLMClientError",
    "ContradictionJudgment",
    "FallbackSuggestion",
    "ChatAnswer",
    "check_contradiction",
    "generate_fallback_language",
    "answer_chat_question",
]


class LocalLLMClientError(AIClientError):
    """Raised when the local model fails to load or produces output that
    doesn't validate against the expected schema even after grammar
    constraint (e.g. a required field the grammar allowed to be omitted
    in some edge case, or a value that fails Pydantic validation)."""


_llm: Llama | None = None
_llm_lock = threading.Lock()


def _get_llm() -> Llama:
    global _llm
    if _llm is None:
        with _llm_lock:
            if _llm is None:
                try:
                    _llm = Llama.from_pretrained(
                        repo_id=settings.LOCAL_LLM_REPO_ID,
                        filename=settings.LOCAL_LLM_FILENAME,
                        n_ctx=settings.LOCAL_LLM_CONTEXT_SIZE,
                        verbose=False,
                    )
                except Exception as e:
                    raise LocalLLMClientError(f"Failed to load local model '{settings.LOCAL_LLM_REPO_ID}': {e}") from e
    return _llm


def _structured_chat_completion(system_prompt: str, user_content: str, schema_model: type) -> str:
    llm = _get_llm()
    # Serialize inference: the underlying llama.cpp context isn't safe for
    # concurrent generation calls from multiple threads (see module docstring).
    with _llm_lock:
        try:
            response = llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                response_format={"type": "json_object", "schema": schema_model.model_json_schema()},
                max_tokens=768,
                temperature=0.1,
            )
        except Exception as e:
            raise LocalLLMClientError(f"Local model inference failed: {e}") from e

    try:
        return response["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise LocalLLMClientError(f"Local model returned an unexpected response shape: {e}") from e


def check_contradiction(
    topic: str, msa_heading: str, msa_text: str, sow_heading: str, sow_text: str
) -> ContradictionJudgment:
    """Sends one MSA/SOW clause pair to the local model and returns a
    structured judgment."""
    user_content = contradiction_user_content(topic, msa_heading, msa_text, sow_heading, sow_text)
    raw = _structured_chat_completion(CONTRADICTION_SYSTEM_PROMPT, user_content, ContradictionJudgment)
    try:
        return ContradictionJudgment.model_validate_json(raw)
    except Exception as e:
        raise LocalLLMClientError(f"Local model response did not match the expected schema: {e}") from e


def generate_fallback_language(
    original_heading: str, original_text: str, risk_reason: str, reference_heading: str | None, reference_text: str | None
) -> FallbackSuggestion:
    """Drafts fallback replacement text for a single flagged clause."""
    user_content = fallback_user_content(original_heading, original_text, risk_reason, reference_heading, reference_text)
    raw = _structured_chat_completion(FALLBACK_SYSTEM_PROMPT, user_content, FallbackSuggestion)
    try:
        return FallbackSuggestion.model_validate_json(raw)
    except Exception as e:
        raise LocalLLMClientError(f"Local model response did not match the expected schema: {e}") from e


def answer_chat_question(context_block: str, history_block: str, question: str) -> ChatAnswer:
    """Answers a Chat with Contract question grounded in already-retrieved
    clause context. Does no retrieval itself, only answer synthesis."""
    user_content = chat_user_content(context_block, history_block, question)
    raw = _structured_chat_completion(CHAT_SYSTEM_PROMPT, user_content, ChatAnswer)
    try:
        return ChatAnswer.model_validate_json(raw)
    except Exception as e:
        raise LocalLLMClientError(f"Local model response did not match the expected schema: {e}") from e
