from unittest.mock import patch

import pytest

from app.models.schema import Clause, DocType, ParsedDocument
from app.services.claude_client import FallbackSuggestion
from app.services.redline_service import generate_redline


def _clause(doc_id: str, doc_type: DocType, section_number: str, heading: str, text: str) -> Clause:
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
    )


def _doc(doc_id: str, doc_type: DocType, clauses: list[Clause]) -> ParsedDocument:
    return ParsedDocument(doc_id=doc_id, filename=f"{doc_id}.pdf", doc_type=doc_type, clauses=clauses)


@pytest.fixture
def sow_and_msa():
    sow = _doc("sow1", DocType.SOW, [
        _clause("sow1", DocType.SOW, "3.3", "Invoice Terms", "Client shall pay invoices within fifteen days of receipt."),
    ])
    msa = _doc("msa1", DocType.MSA, [
        _clause("msa1", DocType.MSA, "5.1", "Invoicing and Payment", "Client shall pay invoices within forty-five days of receipt."),
    ])
    return sow, msa


def _mock_get_document(docs_by_id):
    return lambda doc_id: docs_by_id.get(doc_id)


def test_generate_redline_with_reference_clause(sow_and_msa):
    sow, msa = sow_and_msa
    docs = {"sow1": sow, "msa1": msa}
    fake = FallbackSuggestion(
        suggested_text="Client shall pay invoices within forty-five days of receipt.",
        rationale="Aligned the SOW payment window with the governing MSA's 45-day term.",
    )

    with patch("app.services.redline_service.get_document", side_effect=_mock_get_document(docs)), \
         patch("app.services.redline_service.generate_fallback_language", return_value=fake) as mock_gen:
        result = generate_redline(
            doc_id="sow1",
            clause_id="sow1::3.3",
            risk_reason="Conflicts with MSA Section 5.1, which requires payment within 45 days.",
            reference_doc_id="msa1",
            reference_clause_id="msa1::5.1",
        )

    assert mock_gen.call_count == 1
    call_kwargs = mock_gen.call_args.kwargs
    assert call_kwargs["reference_text"] == "Client shall pay invoices within forty-five days of receipt."
    assert call_kwargs["reference_heading"] == "Invoicing and Payment"

    assert result.doc_id == "sow1"
    assert result.clause_id == "sow1::3.3"
    assert result.original_text == "Client shall pay invoices within fifteen days of receipt."
    assert result.suggested_text == fake.suggested_text
    assert result.rationale == fake.rationale
    assert any(op.type == "delete" and op.text == "fifteen" for op in result.diff)
    assert any(op.type == "insert" and op.text == "forty-five" for op in result.diff)
    assert "~~fifteen~~" in result.diff_markdown
    assert "**forty-five**" in result.diff_markdown


def test_generate_redline_without_reference_clause(sow_and_msa):
    sow, _ = sow_and_msa
    docs = {"sow1": sow}
    fake = FallbackSuggestion(suggested_text="Client shall pay invoices within thirty days of receipt.", rationale="Shortened the payment window.")

    with patch("app.services.redline_service.get_document", side_effect=_mock_get_document(docs)), \
         patch("app.services.redline_service.generate_fallback_language", return_value=fake) as mock_gen:
        result = generate_redline(doc_id="sow1", clause_id="sow1::3.3", risk_reason="Payment window too long.")

    call_kwargs = mock_gen.call_args.kwargs
    assert call_kwargs["reference_text"] is None
    assert call_kwargs["reference_heading"] is None
    assert result.suggested_text == fake.suggested_text


def test_generate_redline_missing_document_raises(sow_and_msa):
    with patch("app.services.redline_service.get_document", return_value=None):
        with pytest.raises(ValueError, match="Document not found"):
            generate_redline(doc_id="nope", clause_id="nope::1", risk_reason="x")


def test_generate_redline_missing_clause_raises(sow_and_msa):
    sow, _ = sow_and_msa
    docs = {"sow1": sow}
    with patch("app.services.redline_service.get_document", side_effect=_mock_get_document(docs)):
        with pytest.raises(ValueError, match="Clause not found"):
            generate_redline(doc_id="sow1", clause_id="sow1::9.9", risk_reason="x")


def test_generate_redline_missing_reference_document_raises(sow_and_msa):
    sow, _ = sow_and_msa
    docs = {"sow1": sow}
    with patch("app.services.redline_service.get_document", side_effect=_mock_get_document(docs)):
        with pytest.raises(ValueError, match="Reference document not found"):
            generate_redline(
                doc_id="sow1", clause_id="sow1::3.3", risk_reason="x",
                reference_doc_id="msa1", reference_clause_id="msa1::5.1",
            )


def test_embedded_pdf_linewrap_newlines_do_not_pollute_the_diff():
    """Regression: PyMuPDF-extracted clause text carries a literal '\\n' at
    each PDF line-wrap point (see Phase 2's structure.py). Claude's generated
    fallback is flowing prose with no such newline. Without whitespace
    normalization this produced a spurious whitespace-only delete/insert
    hunk alongside the real word change."""
    sow = _doc("sow1", DocType.SOW, [
        _clause(
            "sow1", DocType.SOW, "3.3", "Invoice Terms",
            "Client shall pay invoices within fifteen days of\nreceipt.",
        ),
    ])
    docs = {"sow1": sow}
    fake = FallbackSuggestion(
        suggested_text="Client shall pay invoices within forty-five days of receipt.",
        rationale="Aligned with the MSA.",
    )

    with patch("app.services.redline_service.get_document", side_effect=_mock_get_document(docs)), \
         patch("app.services.redline_service.generate_fallback_language", return_value=fake):
        result = generate_redline(doc_id="sow1", clause_id="sow1::3.3", risk_reason="x")

    assert result.original_text == "Client shall pay invoices within fifteen days of receipt."
    # exactly one delete and one insert -- no extra whitespace-only hunks
    deletes = [op for op in result.diff if op.type == "delete"]
    inserts = [op for op in result.diff if op.type == "insert"]
    assert [d.text for d in deletes] == ["fifteen"]
    assert [i.text for i in inserts] == ["forty-five"]
