"""Output models for MSA vs SOW contradiction detection (Phase 5)."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ContradictionStatus(str, Enum):
    ANALYZED = "analyzed"           # the configured AI provider produced a judgment
    CANNOT_EVALUATE = "cannot_evaluate"  # skipped -- a missing reference (Phase 4) blocks either clause
    ERROR = "error"                 # the AI provider call failed after retries


class ContradictionResult(BaseModel):
    topic: str
    msa_clause_id: str
    sow_clause_id: str
    status: ContradictionStatus
    has_contradiction: bool | None = None
    explanation: str | None = None
    confidence: float | None = None  # 0.0-1.0, only set when status == analyzed
    reason: str | None = None        # populated for cannot_evaluate / error


class UnmatchedClause(BaseModel):
    """A clause with body text whose heading matched no configured Playbook
    topic -- it never became a comparison candidate in `results[]` at all,
    not even a `cannot_evaluate` entry. Without this list, that clause is
    silently invisible: contradiction detection never looked at it, and
    nothing says so. See app/contradiction/topic_alignment.py."""

    doc_id: str
    clause_id: str
    section_number: str
    heading: str | None = None


class ContradictionAnalysis(BaseModel):
    msa_doc_id: str
    sow_doc_id: str
    results: list[ContradictionResult] = Field(default_factory=list)
    contradictions_found: int = 0
    unmatched_clauses: list[UnmatchedClause] = Field(default_factory=list)
