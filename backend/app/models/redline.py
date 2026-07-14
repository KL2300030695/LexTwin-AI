"""Output models for redline generation (Phase 6)."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class DiffOpType(str, Enum):
    EQUAL = "equal"
    INSERT = "insert"
    DELETE = "delete"


class DiffOp(BaseModel):
    type: DiffOpType
    text: str


class RedlineSuggestion(BaseModel):
    doc_id: str
    clause_id: str
    original_text: str
    suggested_text: str
    rationale: str
    diff: list[DiffOp] = Field(default_factory=list)
    diff_markdown: str
