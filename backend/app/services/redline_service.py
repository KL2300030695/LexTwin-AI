"""Phase 6: redline generation for a single flagged clause.

Given a clause that some upstream check (a Phase 5 contradiction, a Phase 3
blanket override, or anything else) flagged as risky, ask the configured AI
provider for fallback replacement language (app/services/ai_client, Claude or
Gemini), then compute a deterministic word-level diff between the original
and suggested text (app/redline/diffing.py -- not the LLM).
"""
from __future__ import annotations

import re

from app.models.redline import RedlineSuggestion
from app.models.schema import Clause, ParsedDocument
from app.redline.diffing import diff_to_markdown, word_level_diff
from app.services.ai_client import generate_fallback_language
from app.services.document_service import get_document

_WHITESPACE_RUN_RE = re.compile(r"\s+")


def _normalize_whitespace(text: str) -> str:
    """Collapses whitespace runs (including the mid-sentence line-wrap
    newlines PyMuPDF-extracted clause text carries, see Phase 2) to single
    spaces. Without this, a clause's original PDF line-wrap position vs.
    Claude's flowing-prose suggestion produces a spurious whitespace-only
    diff hunk alongside the real change."""
    return _WHITESPACE_RUN_RE.sub(" ", text).strip()


def _find_clause(doc: ParsedDocument, clause_id: str) -> Clause | None:
    return next((c for c in doc.clauses if c.id == clause_id), None)


def generate_redline(
    doc_id: str,
    clause_id: str,
    risk_reason: str,
    reference_doc_id: str | None = None,
    reference_clause_id: str | None = None,
) -> RedlineSuggestion:
    doc = get_document(doc_id)
    if doc is None:
        raise ValueError(f"Document not found: {doc_id}")
    clause = _find_clause(doc, clause_id)
    if clause is None:
        raise ValueError(f"Clause not found: {clause_id} in document {doc_id}")

    original_text = _normalize_whitespace(clause.text)

    reference_heading: str | None = None
    reference_text: str | None = None
    if reference_doc_id and reference_clause_id:
        reference_doc = get_document(reference_doc_id)
        if reference_doc is None:
            raise ValueError(f"Reference document not found: {reference_doc_id}")
        reference_clause = _find_clause(reference_doc, reference_clause_id)
        if reference_clause is None:
            raise ValueError(f"Reference clause not found: {reference_clause_id} in document {reference_doc_id}")
        reference_heading = reference_clause.heading
        reference_text = _normalize_whitespace(reference_clause.text)

    suggestion = generate_fallback_language(
        original_heading=clause.heading or clause.section_number or "",
        original_text=original_text,
        risk_reason=risk_reason,
        reference_heading=reference_heading,
        reference_text=reference_text,
    )
    suggested_text = _normalize_whitespace(suggestion.suggested_text)

    diffs = word_level_diff(original_text, suggested_text)

    return RedlineSuggestion(
        doc_id=doc_id,
        clause_id=clause_id,
        original_text=original_text,
        suggested_text=suggested_text,
        rationale=suggestion.rationale,
        diff=diffs,
        diff_markdown=diff_to_markdown(diffs),
    )
