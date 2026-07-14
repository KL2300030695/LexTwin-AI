"""Shared helpers for resolving a clause's cross-document reference signals.

Used by both the dependency graph (Phase 3, app/graph/dependency_graph.py)
and the missing-reference / refusal check (Phase 4, app/completeness).
"""
from __future__ import annotations

from app.models.schema import Clause, DocType, Reference, ReferenceType

# "Section 4.2 of the Master Service Agreement" -- a section reference
# immediately followed by a named external document redirects resolution to
# that document instead of the current one. "the Agreement" / "this
# Agreement" are deliberately NOT mapped here: in context they almost always
# mean "this same document", not a cross-document pointer.
EXTERNAL_DOC_TO_DOCTYPE: dict[str, DocType] = {
    "master service agreement": DocType.MSA,
    "statement of work": DocType.SOW,
}
DOCTYPE_TO_EXTERNAL_DOC_LABEL: dict[DocType, str] = {
    DocType.MSA: "Master Service Agreement",
    DocType.SOW: "Statement of Work",
}
MAX_QUALIFIER_GAP = 45  # max chars between "Section X" and "...of the Y" to count as qualifying it


def qualifying_external_doctype(clause: Clause, section_ref: Reference) -> DocType | None:
    """If `section_ref` (a SECTION reference within `clause`) is immediately
    qualified by a named external document (e.g. '...of the Master Service
    Agreement'), returns the DocType that reference should resolve against."""
    for other in clause.references:
        if other.type != ReferenceType.EXTERNAL_DOC or not other.target_label:
            continue
        gap = other.char_start - section_ref.char_end
        if 0 <= gap <= MAX_QUALIFIER_GAP:
            mapped = EXTERNAL_DOC_TO_DOCTYPE.get(other.target_label.lower())
            if mapped is not None:
                return mapped
    return None


def resolve_external_doctype(label: str | None) -> DocType | None:
    """Maps a bare EXTERNAL_DOC reference's label (e.g. from '...governed by
    the Statement of Work...') to the DocType it names, if any."""
    return EXTERNAL_DOC_TO_DOCTYPE.get(label.lower()) if label else None
