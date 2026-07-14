"""Output models for MSA vs SOW contradiction detection (Phase 5)."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ContradictionStatus(str, Enum):
    ANALYZED = "analyzed"           # Claude produced a judgment
    CANNOT_EVALUATE = "cannot_evaluate"  # skipped -- a missing reference (Phase 4) blocks either clause
    ERROR = "error"                 # the LLM call failed after retries


class ContradictionResult(BaseModel):
    topic: str
    msa_clause_id: str
    sow_clause_id: str
    status: ContradictionStatus
    has_contradiction: bool | None = None
    explanation: str | None = None
    confidence: float | None = None  # 0.0-1.0, only set when status == analyzed
    reason: str | None = None        # populated for cannot_evaluate / error


class ContradictionAnalysis(BaseModel):
    msa_doc_id: str
    sow_doc_id: str
    results: list[ContradictionResult] = Field(default_factory=list)
    contradictions_found: int = 0
