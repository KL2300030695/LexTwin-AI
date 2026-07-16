"""Audit trail models: original text, AI risk rating/suggestion, and the
human reviewer's decision, for every flagged clause a reviewer has looked at."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class AuditDecision(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AuditRevision(BaseModel):
    """A prior decision that was later changed. Recorded so a corrected
    decision is a visible, traceable event rather than a silent overwrite --
    the whole point of an audit trail is that "we approved this, then
    realized it was wrong and changed it" is itself part of the record."""

    decision: AuditDecision
    reviewer: str | None = None
    decided_at: str | None = None


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
    # Every decision this entry held before the current one, oldest first.
    # Empty until a decision is changed after already being set once.
    revision_history: list[AuditRevision] = Field(default_factory=list)


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
    """No `reviewer` field here on purpose: who decided is now derived
    server-side from the caller's verified Firebase identity (see
    app/routers/audit.py), not a client-supplied free-text string a caller
    could put any name into."""

    decision: AuditDecision
