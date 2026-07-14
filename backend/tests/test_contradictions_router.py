"""End-to-end check of the /api/contradictions/analyze HTTP endpoint (request
parsing, service wiring, response serialization) with the Claude call mocked
out -- exercises the real FastAPI app without hitting the network or
requiring an API key."""
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.models.schema import Clause, DocType, ParsedDocument
from app.services.claude_client import ContradictionJudgment

client = TestClient(app)


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


def test_analyze_endpoint_returns_contradiction_json():
    msa = _doc("msa1", DocType.MSA, [
        _clause("msa1", DocType.MSA, "5.1", "Invoicing and Payment", "Pay within forty-five days."),
    ])
    sow = _doc("sow1", DocType.SOW, [
        _clause("sow1", DocType.SOW, "3.3", "Invoice Terms", "Pay within fifteen days."),
    ])
    docs = {"msa1": msa, "sow1": sow}

    judgment = ContradictionJudgment(
        has_contradiction=True,
        explanation="45 days vs 15 days is a direct conflict.",
        confidence=0.97,
    )

    with patch("app.services.contradiction_service.get_document", side_effect=lambda doc_id: docs.get(doc_id)), \
         patch("app.services.contradiction_service.check_contradiction", return_value=judgment):
        response = client.post(
            "/api/contradictions/analyze",
            json={"msa_doc_id": "msa1", "sow_doc_id": "sow1"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["msa_doc_id"] == "msa1"
    assert body["sow_doc_id"] == "sow1"
    assert body["contradictions_found"] == 1
    assert len(body["results"]) == 1
    result = body["results"][0]
    assert result["topic"] == "Payment Terms"
    assert result["status"] == "analyzed"
    assert result["has_contradiction"] is True
    assert result["confidence"] == 0.97


def test_analyze_endpoint_404_for_missing_document():
    with patch("app.services.contradiction_service.get_document", return_value=None):
        response = client.post(
            "/api/contradictions/analyze",
            json={"msa_doc_id": "nope", "sow_doc_id": "also-nope"},
        )
    assert response.status_code == 404
