"""Output models for the clause dependency graph (Phase 3)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.models.schema import DocType

EdgeKind = Literal["reference", "notwithstanding_override"]
CircularSeverity = Literal["override_conflict", "circular_reference"]


class GraphNode(BaseModel):
    id: str
    doc_id: str
    doc_type: DocType
    section_number: str
    heading: str | None
    has_general_override: bool


class GraphEdge(BaseModel):
    source: str
    target: str
    kind: EdgeKind
    raw_text: str
    context: str


class NotwithstandingOverride(BaseModel):
    overriding_clause_id: str
    overridden_clause_id: str
    raw_text: str


class GeneralOverride(BaseModel):
    """A 'Notwithstanding anything to the contrary...' with no specific target."""

    clause_id: str
    snippet: str


class UnresolvedReference(BaseModel):
    """A section reference that couldn't be resolved to any clause in the
    analyzed document set -- either it targets a section that doesn't exist,
    or it names another document (e.g. 'of the Master Service Agreement')
    that wasn't included in this analysis."""

    clause_id: str
    raw_text: str
    target_section: str
    context: str


class CircularReferenceGroup(BaseModel):
    clause_ids: list[str]
    severity: CircularSeverity
    edges: list[GraphEdge]


class GraphAnalysis(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    overrides: list[NotwithstandingOverride] = Field(default_factory=list)
    general_overrides: list[GeneralOverride] = Field(default_factory=list)
    unresolved_references: list[UnresolvedReference] = Field(default_factory=list)
    circular_references: list[CircularReferenceGroup] = Field(default_factory=list)
