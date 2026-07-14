from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.contradiction import ContradictionAnalysis
from app.services.contradiction_service import analyze_contradictions

router = APIRouter()


class ContradictionAnalyzeRequest(BaseModel):
    msa_doc_id: str
    sow_doc_id: str


@router.post("/analyze", response_model=ContradictionAnalysis)
def analyze(payload: ContradictionAnalyzeRequest):
    try:
        return analyze_contradictions(payload.msa_doc_id, payload.sow_doc_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
