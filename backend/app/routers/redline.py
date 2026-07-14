from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.redline import RedlineSuggestion
from app.services.redline_service import generate_redline

router = APIRouter()


class RedlineGenerateRequest(BaseModel):
    doc_id: str
    clause_id: str
    risk_reason: str
    reference_doc_id: str | None = None
    reference_clause_id: str | None = None


@router.post("/generate", response_model=RedlineSuggestion)
def generate(payload: RedlineGenerateRequest):
    try:
        return generate_redline(
            doc_id=payload.doc_id,
            clause_id=payload.clause_id,
            risk_reason=payload.risk_reason,
            reference_doc_id=payload.reference_doc_id,
            reference_clause_id=payload.reference_clause_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
