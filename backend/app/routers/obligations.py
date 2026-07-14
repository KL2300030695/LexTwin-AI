from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.obligation import Obligation
from app.services.obligation_service import extract_obligations_for_docs

router = APIRouter()


class ObligationExtractRequest(BaseModel):
    doc_ids: list[str]


@router.post("/extract", response_model=list[Obligation])
def extract(payload: ObligationExtractRequest):
    try:
        return extract_obligations_for_docs(payload.doc_ids)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
