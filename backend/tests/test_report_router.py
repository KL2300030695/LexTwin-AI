from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_generate_endpoint_returns_a_pdf():
    response = client.post(
        "/api/report/generate",
        json={
            "msa_filename": "msa_sample.pdf",
            "sow_filename": "sow_sample.pdf",
            "risk_flags": [
                {"id": "f1", "kind": "contradiction", "severity": "high", "title": "Payment Terms conflict", "description": "45 vs 15 days", "confidence": 0.97}
            ],
            "obligations": [],
            "audit_entries": [],
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert response.content[:4] == b"%PDF"
    assert len(response.content) > 0


def test_generate_endpoint_sanitizes_filenames_with_unsafe_characters():
    response = client.post(
        "/api/report/generate",
        json={"msa_filename": "my msa (v2).pdf", "sow_filename": "sow/2026.pdf"},
    )
    assert response.status_code == 200
    disposition = response.headers["content-disposition"]
    assert "/" not in disposition.split("filename=")[1]
    assert "(" not in disposition


def test_generate_endpoint_works_with_minimal_payload():
    response = client.post(
        "/api/report/generate",
        json={"msa_filename": "msa.pdf", "sow_filename": "sow.pdf"},
    )
    assert response.status_code == 200
    assert response.content[:4] == b"%PDF"
