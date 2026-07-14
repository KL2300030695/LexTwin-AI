"""Audit trail models: original text, AI risk rating/suggestion, and the
human reviewer's decision, for every flagged clause a reviewer has looked at."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class AuditDecision(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AuditEntry(BaseModel):
    id: str
    msa_doc_id: str
    sow_doc_id: str
    doc_id: str  # which document the flagged clause belongs to
    clause_id: str
    topic: str | None = None
    original_text: str
    risk_rating: str  # e.g. "contradiction", "circular_reference", "missing_reference", or a free-text reason
    ai_suggestion: str | None = None
    ai_rationale: str | None = None
    decision: AuditDecision = AuditDecision.PENDING
    reviewer: str | None = None
    created_at: str
    decided_at: str | None = None


class AuditEntryCreate(BaseModel):
    msa_doc_id: str
    sow_doc_id: str
    doc_id: str
    clause_id: str
    topic: str | None = None
    original_text: str
    risk_rating: str
    ai_suggestion: str | None = None
    ai_rationale: str | None = None


class AuditDecisionUpdate(BaseModel):
    decision: AuditDecision
    reviewer: str | None = None
