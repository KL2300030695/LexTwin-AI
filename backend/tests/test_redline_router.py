from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.models.schema import Clause, DocType, ParsedDocument
from app.services.claude_client import FallbackSuggestion

client = TestClient(app)


def _clause(doc_id, doc_type, section_number, heading, text):
    return Clause(
        id=f"{doc_id}::{section_number}", doc_id=doc_id, doc_type=doc_type, section_number=section_number,
        parent_section=None, level=1, heading=heading, text=text, page_start=1, page_end=1,
    )


def test_redline_generate_endpoint_returns_diff():
    sow = ParsedDocument(
        doc_id="sow1", filename="sow1.pdf", doc_type=DocType.SOW,
        clauses=[_clause("sow1", DocType.SOW, "3.3", "Invoice Terms", "Pay within fifteen days.")],
    )
    docs = {"sow1": sow}
    fake = FallbackSuggestion(suggested_text="Pay within forty-five days.", rationale="Aligned with MSA.")

    with patch("app.services.redline_service.get_document", side_effect=lambda d: docs.get(d)), \
         patch("app.services.redline_service.generate_fallback_language", return_value=fake):
        response = client.post(
            "/api/redline/generate",
            json={"doc_id": "sow1", "clause_id": "sow1::3.3", "risk_reason": "Conflicts with MSA."},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["original_text"] == "Pay within fifteen days."
    assert body["suggested_text"] == "Pay within forty-five days."
    assert body["rationale"] == "Aligned with MSA."
    assert "~~fifteen~~" in body["diff_markdown"]
    assert "**forty-five**" in body["diff_markdown"]
    assert len(body["diff"]) > 0


def test_redline_generate_endpoint_404_for_missing_clause():
    sow = ParsedDocument(doc_id="sow1", filename="sow1.pdf", doc_type=DocType.SOW, clauses=[])
    docs = {"sow1": sow}
    with patch("app.services.redline_service.get_document", side_effect=lambda d: docs.get(d)):
        response = client.post(
            "/api/redline/generate",
            json={"doc_id": "sow1", "clause_id": "sow1::9.9", "risk_reason": "x"},
        )
    assert response.status_code == 404
