from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.chat import ChatRequest, ChatResponse
from app.services.chat_service import answer_question

router = APIRouter()


@router.post("/ask", response_model=ChatResponse)
def ask(payload: ChatRequest):
    try:
        return answer_question(payload.doc_ids, payload.question, payload.history)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
