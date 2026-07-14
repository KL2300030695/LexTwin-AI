from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.graph import GraphAnalysis
from app.services.graph_service import analyze_graph

router = APIRouter()


class GraphAnalyzeRequest(BaseModel):
    doc_ids: list[str]


@router.post("/analyze", response_model=GraphAnalysis)
def analyze(payload: GraphAnalyzeRequest):
    try:
        return analyze_graph(payload.doc_ids)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
