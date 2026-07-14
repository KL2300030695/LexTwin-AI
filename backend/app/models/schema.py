"""Core data models shared across the parsing, graph, and API layers."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DocType(str, Enum):
    MSA = "MSA"
    SOW = "SOW"
    OTHER = "OTHER"


class ReferenceType(str, Enum):
    SECTION = "section"          # "Section 4.2"
    EXHIBIT = "exhibit"          # "Exhibit B"
    APPENDIX = "appendix"        # "Appendix 1"
    ANNEXURE = "annexure"        # "Annexure A"
    SCHEDULE = "schedule"        # "Schedule 2"
    EXTERNAL_DOC = "external_doc"  # "Master Service Agreement dated..."


class Reference(BaseModel):
    """A cross-reference found inside a clause's text."""

    raw_text: str
    type: ReferenceType
    target_section: Optional[str] = None   # normalized, e.g. "4.2" (section refs)
    target_label: Optional[str] = None     # normalized, e.g. "Exhibit B" (external refs)
    is_notwithstanding: bool = False
    char_start: int = 0
    char_end: int = 0
    context: str = ""


class TableModel(BaseModel):
    id: str
    clause_id: Optional[str] = None
    page: int
    rows: list[list[str]] = Field(default_factory=list)
    header: Optional[list[str]] = None


class Clause(BaseModel):
    id: str                       # f"{doc_id}::{section_number}"
    doc_id: str
    doc_type: DocType
    section_number: Optional[str] = None   # "4.2.1"
    parent_section: Optional[str] = None   # "4.2"
    level: int = 0                          # depth, top-level headings = 1
    heading: Optional[str] = None
    text: str
    page_start: int
    page_end: int
    references: list[Reference] = Field(default_factory=list)
    table_ids: list[str] = Field(default_factory=list)


class ParsedDocument(BaseModel):
    doc_id: str
    filename: str
    doc_type: DocType
    clauses: list[Clause] = Field(default_factory=list)
    tables: list[TableModel] = Field(default_factory=list)
    page_count: int = 0
    # Exhibits/appendices/annexures/schedules mentioned but not necessarily uploaded
    known_exhibit_labels: list[str] = Field(default_factory=list)
    # Exhibit labels that were actually uploaded/present in the doc set
    available_exhibit_labels: list[str] = Field(default_factory=list)
