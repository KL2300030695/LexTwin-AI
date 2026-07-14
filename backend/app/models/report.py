"""Request model for the downloadable PDF risk report.

The frontend has already fetched/derived everything a report needs for the
on-screen dashboard (risk flags, obligations, audit trail) -- this endpoint
only formats that data into a PDF. It never re-runs graph/completeness
analysis and never makes a new AI provider call, so the report always
matches exactly what the reviewer saw on screen (and never re-triggers a
billed/quota-limited AI request just to produce a document)."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.audit import AuditEntry
from app.models.obligation import Obligation


class ReportRiskFlag(BaseModel):
    id: str
    kind: str
    severity: str
    title: str
    description: str = ""
    clause_ids: list[str] = Field(default_factory=list)
    # Only set for contradiction flags -- 0.0-1.0.
    confidence: float | None = None


class ReportRequest(BaseModel):
    msa_filename: str
    sow_filename: str
    risk_flags: list[ReportRiskFlag] = Field(default_factory=list)
    obligations: list[Obligation] = Field(default_factory=list)
    audit_entries: list[AuditEntry] = Field(default_factory=list)
