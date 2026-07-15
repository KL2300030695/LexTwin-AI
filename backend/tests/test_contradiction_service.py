"""Tests the contradiction detection pipeline (alignment -> Phase 4 gating ->
local model judgment) with the model call mocked out -- these must never
load the real (multi-GB) model or run real inference. See
test_contradiction_integration_llm.py for the real-model smoke test
(marked slow)."""
from unittest.mock import patch

import pytest

from app.models.contradiction import ContradictionStatus
from app.models.schema import Clause, DocType, ParsedDocument, Reference, ReferenceType
from app.services.ai_schemas import ContradictionJudgment
from app.services.local_llm_client import LocalLLMClientError
from app.services.contradiction_service import analyze_contradictions


def _clause(doc_id: str, doc_type: DocType, section_number: str, heading: str, text: str, references: list[Reference] | None = None) -> Clause:
    return Clause(
        id=f"{doc_id}::{section_number}",
        doc_id=doc_id,
        doc_type=doc_type,
        section_number=section_number,
        parent_section=None,
        level=1,
        heading=heading,
        text=text,
        page_start=1,
        page_end=1,
        references=references or [],
    )


def _doc(doc_id: str, doc_type: DocType, clauses: list[Clause]) -> ParsedDocument:
    return ParsedDocument(doc_id=doc_id, filename=f"{doc_id}.pdf", doc_type=doc_type, clauses=clauses)


@pytest.fixture
def msa_and_sow():
    msa = _doc("msa1", DocType.MSA, [
        _clause("msa1", DocType.MSA, "5.1", "Invoicing and Payment", "Client shall pay within forty-five days."),
    ])
    sow = _doc("sow1", DocType.SOW, [
        _clause("sow1", DocType.SOW, "3.3", "Invoice Terms", "Client shall pay within fifteen days."),
    ])
    return msa, sow


def _mock_get_document(docs_by_id):
    def _get(doc_id):
        return docs_by_id.get(doc_id)
    return _get


def test_analyzed_pair_calls_local_model_and_records_judgment(msa_and_sow):
    msa, sow = msa_and_sow
    docs = {"msa1": msa, "sow1": sow}

    fake_judgment = ContradictionJudgment(
        has_contradiction=True,
        explanation="MSA requires payment within 45 days; SOW requires payment within 15 days.",
        confidence=0.95,
    )

    with patch("app.services.contradiction_service.get_document", side_effect=_mock_get_document(docs)), \
         patch("app.services.contradiction_service.check_contradiction", return_value=fake_judgment) as mock_check:
        result = analyze_contradictions("msa1", "sow1")

    assert mock_check.call_count == 1
    assert len(result.results) == 1
    r = result.results[0]
    assert r.status == ContradictionStatus.ANALYZED
    assert r.has_contradiction is True
    assert r.confidence == 0.95
    assert result.contradictions_found == 1


def test_no_contradiction_judgment_not_counted(msa_and_sow):
    msa, sow = msa_and_sow
    docs = {"msa1": msa, "sow1": sow}
    fake_judgment = ContradictionJudgment(has_contradiction=False, explanation="Consistent.", confidence=0.8)

    with patch("app.services.contradiction_service.get_document", side_effect=_mock_get_document(docs)), \
         patch("app.services.contradiction_service.check_contradiction", return_value=fake_judgment):
        result = analyze_contradictions("msa1", "sow1")

    assert result.results[0].has_contradiction is False
    assert result.contradictions_found == 0


def test_missing_reference_blocks_pair_without_calling_local_model():
    """A clause that references a missing exhibit must be skipped entirely --
    The local model must never be asked to reason about content it wasn't given."""
    msa = _doc("msa1", DocType.MSA, [
        _clause(
            "msa1", DocType.MSA, "5.1", "Invoicing and Payment",
            "See Exhibit C for the fee schedule.",
            references=[Reference(raw_text="Exhibit C", type=ReferenceType.EXHIBIT, target_label="Exhibit C", context="See Exhibit C")],
        ),
    ])
    sow = _doc("sow1", DocType.SOW, [
        _clause("sow1", DocType.SOW, "3.3", "Invoice Terms", "Client shall pay within fifteen days."),
    ])
    docs = {"msa1": msa, "sow1": sow}

    with patch("app.services.contradiction_service.get_document", side_effect=_mock_get_document(docs)), \
         patch("app.services.contradiction_service.check_contradiction") as mock_check:
        result = analyze_contradictions("msa1", "sow1")

    mock_check.assert_not_called()
    assert len(result.results) == 1
    r = result.results[0]
    assert r.status == ContradictionStatus.CANNOT_EVALUATE
    assert "Exhibit C" in r.reason
    assert result.contradictions_found == 0


def test_local_model_error_recorded_as_error_status(msa_and_sow):
    msa, sow = msa_and_sow
    docs = {"msa1": msa, "sow1": sow}

    with patch("app.services.contradiction_service.get_document", side_effect=_mock_get_document(docs)), \
         patch("app.services.contradiction_service.check_contradiction", side_effect=LocalLLMClientError("model unavailable")):
        result = analyze_contradictions("msa1", "sow1")

    assert len(result.results) == 1
    r = result.results[0]
    assert r.status == ContradictionStatus.ERROR
    assert "model unavailable" in r.reason
    assert result.contradictions_found == 0


def test_missing_document_raises_value_error():
    with patch("app.services.contradiction_service.get_document", return_value=None):
        with pytest.raises(ValueError):
            analyze_contradictions("nope", "also-nope")


def test_no_shared_topics_produces_no_results():
    msa = _doc("msa1", DocType.MSA, [_clause("msa1", DocType.MSA, "1", "Definitions", "text")])
    sow = _doc("sow1", DocType.SOW, [_clause("sow1", DocType.SOW, "1", "Purpose", "text")])
    docs = {"msa1": msa, "sow1": sow}

    with patch("app.services.contradiction_service.get_document", side_effect=_mock_get_document(docs)), \
         patch("app.services.contradiction_service.check_contradiction") as mock_check:
        result = analyze_contradictions("msa1", "sow1")

    mock_check.assert_not_called()
    assert result.results == []
    assert result.contradictions_found == 0
