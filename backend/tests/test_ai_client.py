"""Tests that app/services/ai_client.py -- the single entry point
contradiction_service.py, redline_service.py, and chat_service.py all
import from -- correctly re-exports local_llm_client.py's functions and
error type.

ai_client.check_contradiction IS local_llm_client.check_contradiction (a
direct `from ... import`, not a wrapper function that calls through at
runtime), so there's no real "delegation" to mock -- the meaningful thing to
verify is that the re-export wiring itself is correct: the same function
object is reachable under both names, and the error hierarchy holds."""
from app.services import ai_client, local_llm_client
from app.services.ai_client import AIClientError
from app.services.local_llm_client import LocalLLMClientError


def test_check_contradiction_is_reexported_from_local_llm_client():
    assert ai_client.check_contradiction is local_llm_client.check_contradiction


def test_generate_fallback_language_is_reexported_from_local_llm_client():
    assert ai_client.generate_fallback_language is local_llm_client.generate_fallback_language


def test_answer_chat_question_is_reexported_from_local_llm_client():
    assert ai_client.answer_chat_question is local_llm_client.answer_chat_question


def test_local_llm_client_error_is_an_ai_client_error():
    assert issubclass(LocalLLMClientError, AIClientError)
