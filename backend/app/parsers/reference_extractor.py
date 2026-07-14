"""Regex-based extraction of cross-references from clause text.

Deterministic on purpose -- reference resolution feeds the dependency graph
and refusal logic, so it must not depend on an LLM's mood.
"""
from __future__ import annotations

import re

from app.models.schema import Reference, ReferenceType

_NUM_RE = r"\d+(?:\.\d+)*"

# "Section 4.2", "Sections 4.2 and 4.3", "Clause 5", "§4.2"
_SECTION_RE = re.compile(
    rf"\b(Section|Sections|Clause|Clauses|§)\s+({_NUM_RE}(?:\s*(?:,|and|&)\s*{_NUM_RE})*)",
    re.IGNORECASE,
)

# "Exhibit B", "Appendix 1", "Annexure A", "Schedule 2", "Exhibit B-1".
# Keyword must be capitalized (a defined-term reference), not a lowercase
# generic use of the word (e.g. "the fees or schedule described below").
# The identifier must look like a label -- a letter+digits or digits+letter,
# not an arbitrary word -- so "Schedule described" can't match "described".
_EXHIBIT_RE = re.compile(
    r"\b(Exhibit|EXHIBIT|Appendix|APPENDIX|Annexure|ANNEXURE|Annex|ANNEX|Schedule|SCHEDULE)"
    r"\s+([A-Z]\d*|\d+[A-Z]?)(?:-[A-Za-z0-9]+)?\b"
)

_EXHIBIT_TYPE_MAP = {
    "exhibit": ReferenceType.EXHIBIT,
    "appendix": ReferenceType.APPENDIX,
    "annexure": ReferenceType.ANNEXURE,
    "annex": ReferenceType.ANNEXURE,
    "schedule": ReferenceType.SCHEDULE,
}

_NOTWITHSTANDING_RE = re.compile(r"\bNotwithstanding\b", re.IGNORECASE)

# Named external documents (not exhibits/appendices, but other governing docs)
_EXTERNAL_DOC_RE = re.compile(
    r"\b(Master Service Agreement|Statement of Work|the Agreement)\b"
)


def _notwithstanding_spans(text: str) -> list[tuple[int, int]]:
    """Char ranges (start of 'Notwithstanding' to end of that sentence) that
    represent an override clause, e.g. 'Notwithstanding Section 4.2, ...'."""
    spans = []
    for m in _NOTWITHSTANDING_RE.finditer(text):
        start = m.start()
        # sentence end = next period, or 250 chars out, whichever is first
        period_idx = text.find(".", start)
        end = period_idx if 0 <= period_idx - start <= 250 else start + 250
        if end == -1:
            end = len(text)
        spans.append((start, end))
    return spans


def _within_any_span(idx: int, spans: list[tuple[int, int]]) -> bool:
    return any(s <= idx < e for s, e in spans)


def extract_references(text: str) -> tuple[list[Reference], bool]:
    """Returns (references, has_general_notwithstanding).

    has_general_notwithstanding is True when the clause contains a
    'Notwithstanding ...' override that does NOT name a specific target
    section (e.g. 'Notwithstanding anything to the contrary herein') --
    i.e. an override whose precedence target can't be resolved to a node.
    """
    references: list[Reference] = []
    nw_spans = _notwithstanding_spans(text)
    nw_span_has_target = [False] * len(nw_spans)

    for m in _SECTION_RE.finditer(text):
        numbers = re.findall(_NUM_RE, m.group(2))
        is_nw = _within_any_span(m.start(), nw_spans)
        if is_nw:
            for i, (s, e) in enumerate(nw_spans):
                if s <= m.start() < e:
                    nw_span_has_target[i] = True
        ctx_start = max(0, m.start() - 40)
        ctx_end = min(len(text), m.end() + 40)
        for num in numbers:
            references.append(
                Reference(
                    raw_text=m.group(0),
                    type=ReferenceType.SECTION,
                    target_section=num,
                    is_notwithstanding=is_nw,
                    char_start=m.start(),
                    char_end=m.end(),
                    context=text[ctx_start:ctx_end].strip(),
                )
            )

    for m in _EXHIBIT_RE.finditer(text):
        kind = m.group(1).lower()
        ref_type = _EXHIBIT_TYPE_MAP[kind]
        label = f"{m.group(1).title()} {m.group(2).upper()}"
        ctx_start = max(0, m.start() - 40)
        ctx_end = min(len(text), m.end() + 40)
        references.append(
            Reference(
                raw_text=m.group(0),
                type=ref_type,
                target_label=label,
                is_notwithstanding=_within_any_span(m.start(), nw_spans),
                char_start=m.start(),
                char_end=m.end(),
                context=text[ctx_start:ctx_end].strip(),
            )
        )

    for m in _EXTERNAL_DOC_RE.finditer(text):
        ctx_start = max(0, m.start() - 40)
        ctx_end = min(len(text), m.end() + 40)
        references.append(
            Reference(
                raw_text=m.group(0),
                type=ReferenceType.EXTERNAL_DOC,
                target_label=m.group(0),
                is_notwithstanding=_within_any_span(m.start(), nw_spans),
                char_start=m.start(),
                char_end=m.end(),
                context=text[ctx_start:ctx_end].strip(),
            )
        )

    has_general_notwithstanding = any(not has_target for has_target in nw_span_has_target) or (
        len(nw_spans) > 0 and not any(nw_span_has_target)
    )
    return references, has_general_notwithstanding
