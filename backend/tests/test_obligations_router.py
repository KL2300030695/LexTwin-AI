"""End-to-end check of the /api/obligations/extract HTTP endpoint (request
parsing, service wiring, response serialization) against the real FastAPI
app, with document lookup mocked out."""
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.models.schema import Clause, DocType, ParsedDocument

client = TestClient(app)


def _clause(doc_id: str, section_number: str, text: str) -> Clause:
    return Clause(
        id=f"{doc_id}::{section_number}",
        doc_id=doc_id,
        doc_type=DocType.MSA,
        section_number=section_number,
        parent_section=None,
        level=1,
        heading=f"Clause {section_number}",
        text=text,
        page_start=2,
        page_end=2,
    )


def _doc(doc_id: str, clauses: list[Clause]) -> ParsedDocument:
    return ParsedDocument(doc_id=doc_id, filename=f"{doc_id}.pdf", doc_type=DocType.MSA, clauses=clauses)


def test_extract_endpoint_returns_obligations_sorted_by_deadline():
    msa = _doc("msa1", [
        _clause("msa1", "7.1", "Each party shall protect Confidential Information."),
        _clause("msa1", "5.1", "Client shall pay all undisputed invoices within forty-five days of receipt."),
    ])
    sow = _doc("sow1", [
        _clause("sow1", "3.3", "Client shall pay invoices within fifteen days of receipt."),
    ])
    docs = {"msa1": msa, "sow1": sow}

    with patch("app.services.obligation_service.get_document", side_effect=lambda doc_id: docs.get(doc_id)):
        response = client.post("/api/obligations/extract", json={"doc_ids": ["msa1", "sow1"]})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 3
    with_deadlines = [o for o in body if o["deadline_days"] is not None]
    assert [o["deadline_days"] for o in with_deadlines] == sorted(o["deadline_days"] for o in with_deadlines)
    assert with_deadlines[0]["deadline_days"] == 15
    assert with_deadlines[1]["deadline_days"] == 45


def test_extract_endpoint_404_for_missing_document():
    with patch("app.services.obligation_service.get_document", return_value=None):
        response = client.post("/api/obligations/extract", json={"doc_ids": ["nope"]})
    assert response.status_code == 404
