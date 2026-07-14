"""Tests chat_service.py's orchestration logic (citation mapping, error
handling, empty-clause edge case) with the embedding model and AI provider
both mocked out -- fast, no real model load or network call."""
from unittest.mock import patch

import numpy as np
import pytest

from app.models.chat import ChatMessage
from app.models.schema import Clause, DocType, ParsedDocument
from app.services.ai_schemas import ChatAnswer
from app.services.chat_service import answer_question


def _clause(section_number: str, heading: str, text: str, doc_id: str = "d1") -> Clause:
    return Clause(
        id=f"{doc_id}::{section_number}", doc_id=doc_id, doc_type=DocType.MSA, section_number=section_number,
        parent_section=None, level=1, heading=heading, text=text, page_start=1, page_end=1,
    )


def _doc(doc_id: str, clauses: list[Clause]) -> ParsedDocument:
    return ParsedDocument(doc_id=doc_id, filename=f"{doc_id}.pdf", doc_type=DocType.MSA, clauses=clauses)


@pytest.fixture(autouse=True)
def _clear_index_cache():
    import app.services.chat_service as chat_service_module

    chat_service_module._index_cache.clear()
    yield
    chat_service_module._index_cache.clear()


def test_answer_question_maps_cited_refs_back_to_clause_citations():
    clause_a = _clause("5.1", "Invoicing and Payment", "Client shall pay within forty-five days.")
    clause_b = _clause("7.1", "Confidentiality", "Each party shall protect confidential information.")
    doc = _doc("msa-1", [clause_a, clause_b])
    fake_retrieved = [(clause_a, 0.9), (clause_b, 0.5)]
    fake_answer = ChatAnswer(answer="Payment is due within 45 days.", cited_refs=[1])

    with patch("app.services.chat_service.get_document", return_value=doc), \
         patch("app.services.chat_service.embed_query", return_value=np.zeros(1024, dtype="float32")), \
         patch("app.services.chat_service.build_clause_index", return_value="fake-index"), \
         patch("app.services.chat_service.search_clause_index", return_value=fake_retrieved), \
         patch("app.services.chat_service.answer_chat_question", return_value=fake_answer) as mock_answer:
        result = answer_question(["msa-1"], "When is payment due?", [])

    assert result.answer == "Payment is due within 45 days."
    assert len(result.citations) == 1
    assert result.citations[0].clause_id == "d1::5.1"
    assert result.citations[0].section_number == "5.1"
    mock_answer.assert_called_once()


def test_answer_question_ignores_out_of_range_cited_refs():
    clause_a = _clause("5.1", "Invoicing and Payment", "Client shall pay within forty-five days.")
    doc = _doc("msa-1", [clause_a])
    fake_answer = ChatAnswer(answer="Some answer.", cited_refs=[1, 99, 0])

    with patch("app.services.chat_service.get_document", return_value=doc), \
         patch("app.services.chat_service.embed_query", return_value=np.zeros(1024, dtype="float32")), \
         patch("app.services.chat_service.build_clause_index", return_value="fake-index"), \
         patch("app.services.chat_service.search_clause_index", return_value=[(clause_a, 0.9)]), \
         patch("app.services.chat_service.answer_chat_question", return_value=fake_answer):
        result = answer_question(["msa-1"], "question", [])

    assert len(result.citations) == 1
    assert result.citations[0].clause_id == "d1::5.1"


def test_answer_question_raises_for_missing_document():
    with patch("app.services.chat_service.get_document", return_value=None):
        with pytest.raises(ValueError, match="Document not found"):
            answer_question(["nope"], "question", [])


def test_answer_question_with_no_analyzable_clauses_skips_ai_call():
    preamble = Clause(
        id="d1::preamble", doc_id="d1", doc_type=DocType.MSA, section_number=None, parent_section=None,
        level=0, heading="Preamble", text="intro", page_start=1, page_end=1,
    )
    doc = _doc("msa-1", [preamble])

    with patch("app.services.chat_service.get_document", return_value=doc), \
         patch("app.services.chat_service.answer_chat_question") as mock_answer:
        result = answer_question(["msa-1"], "question", [])

    assert "No analyzable clauses" in result.answer
    assert result.citations == []
    mock_answer.assert_not_called()


def test_inline_bracketed_reference_markers_are_stripped_from_the_answer():
    """The prompt asks the model not to inline '[1]'-style markers in the
    answer text (citations render separately as chips) -- this is a
    defensive cleanup for when a model doesn't fully comply."""
    clause_a = _clause("5.1", "Invoicing and Payment", "Client shall pay within forty-five days.")
    doc = _doc("msa-1", [clause_a])
    fake_answer = ChatAnswer(answer="Payment is due within 45 days [1], per the MSA [1].", cited_refs=[1])

    with patch("app.services.chat_service.get_document", return_value=doc), \
         patch("app.services.chat_service.embed_query", return_value=np.zeros(1024, dtype="float32")), \
         patch("app.services.chat_service.build_clause_index", return_value="fake-index"), \
         patch("app.services.chat_service.search_clause_index", return_value=[(clause_a, 0.9)]), \
         patch("app.services.chat_service.answer_chat_question", return_value=fake_answer):
        result = answer_question(["msa-1"], "When is payment due?", [])

    assert "[1]" not in result.answer
    assert result.answer == "Payment is due within 45 days, per the MSA."


def test_conversation_history_is_passed_through_to_the_ai_provider():
    clause_a = _clause("5.1", "Invoicing and Payment", "Client shall pay within forty-five days.")
    doc = _doc("msa-1", [clause_a])
    history = [ChatMessage(role="user", content="What are the payment terms?"), ChatMessage(role="assistant", content="45 days.")]
    fake_answer = ChatAnswer(answer="Follow-up answer.", cited_refs=[])

    with patch("app.services.chat_service.get_document", return_value=doc), \
         patch("app.services.chat_service.embed_query", return_value=np.zeros(1024, dtype="float32")), \
         patch("app.services.chat_service.build_clause_index", return_value="fake-index"), \
         patch("app.services.chat_service.search_clause_index", return_value=[(clause_a, 0.9)]), \
         patch("app.services.chat_service.answer_chat_question", return_value=fake_answer) as mock_answer:
        answer_question(["msa-1"], "And what about late fees?", history)

    _context_arg, history_arg, question_arg = mock_answer.call_args[0]
    assert "What are the payment terms?" in history_arg
    assert "45 days." in history_arg
    assert question_arg == "And what about late fees?"
