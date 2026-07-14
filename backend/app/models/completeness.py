"""Output models for the missing-reference / refusal check (Phase 4)."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from app.models.schema import DocType


class MissingReferenceType(str, Enum):
    EXHIBIT = "exhibit"
    APPENDIX = "appendix"
    ANNEXURE = "annexure"
    SCHEDULE = "schedule"
    EXTERNAL_DOCUMENT = "external_document"


class MissingReference(BaseModel):
    label: str  # e.g. "Exhibit C", or "Master Service Agreement", or "Section 4.2 (Master Service Agreement)"
    type: MissingReferenceType
    raw_text: str
    context: str


class ClauseEvaluationStatus(BaseModel):
    clause_id: str
    doc_id: str
    section_number: str
    can_evaluate: bool
    missing_references: list[MissingReference] = Field(default_factory=list)
    reason: str | None = None


class CompletenessAnalysis(BaseModel):
    analyzed_doc_ids: list[str] = Field(default_factory=list)
    available_doc_types: list[DocType] = Field(default_factory=list)
    available_exhibit_labels: list[str] = Field(default_factory=list)
    clause_statuses: list[ClauseEvaluationStatus] = Field(default_factory=list)
    blocked_clause_count: int = 0
    total_clause_count: int = 0
