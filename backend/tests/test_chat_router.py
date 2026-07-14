from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.models.chat import ChatCitation, ChatResponse

client = TestClient(app)


def test_ask_endpoint_returns_answer_and_citations():
    fake_response = ChatResponse(
        answer="Payment is due within 45 days.",
        citations=[ChatCitation(clause_id="msa-1::5.1", doc_id="msa-1", section_number="5.1", heading="Invoicing and Payment")],
    )
    with patch("app.routers.chat.answer_question", return_value=fake_response):
        response = client.post(
            "/api/chat/ask",
            json={"doc_ids": ["msa-1", "sow-1"], "question": "When is payment due?", "history": []},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Payment is due within 45 days."
    assert body["citations"][0]["section_number"] == "5.1"


def test_ask_endpoint_404_for_missing_document():
    with patch("app.routers.chat.answer_question", side_effect=ValueError("Document not found: nope")):
        response = client.post("/api/chat/ask", json={"doc_ids": ["nope"], "question": "question", "history": []})
    assert response.status_code == 404


def test_ask_endpoint_accepts_conversation_history():
    fake_response = ChatResponse(answer="Follow-up.", citations=[])
    with patch("app.routers.chat.answer_question", return_value=fake_response) as mock_answer:
        response = client.post(
            "/api/chat/ask",
            json={
                "doc_ids": ["msa-1"],
                "question": "And late fees?",
                "history": [{"role": "user", "content": "Payment terms?"}, {"role": "assistant", "content": "45 days."}],
            },
        )
    assert response.status_code == 200
    _doc_ids, question, history = mock_answer.call_args[0]
    assert question == "And late fees?"
    assert len(history) == 2
