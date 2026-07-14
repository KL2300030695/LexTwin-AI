from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.completeness import CompletenessAnalysis
from app.services.completeness_service import check_completeness_for_docs

router = APIRouter()


class CompletenessCheckRequest(BaseModel):
    doc_ids: list[str]


@router.post("/check", response_model=CompletenessAnalysis)
def check(payload: CompletenessCheckRequest):
    try:
        return check_completeness_for_docs(payload.doc_ids)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
