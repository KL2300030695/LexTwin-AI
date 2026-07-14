"""Shared clause/heading hierarchy builder used by both the PDF and DOCX parsers.

Both parsers reduce their source format down to a common intermediate form:
  - a list of `Line` records (text + page number), in reading order
  - a list of `TableAnchor` records saying "this table appears after line index N"

This module turns that intermediate form into a `ParsedDocument` (clauses with
section hierarchy + references, tables attached to their owning clause).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.models.schema import Clause, DocType, ParsedDocument, TableModel
from app.parsers.reference_extractor import extract_references

# Matches a heading line like "4.2.1 Penalty Calculation Method" or "4. PAYMENT TERMS"
# The whole line (after stripping) must be number(s) + a short title -- this avoids
# matching in-sentence references like "as described in Section 4.2 above".
_HEADING_RE = re.compile(
    r"^(?P<num>\d+(?:\.\d+){0,4})\.?\s+(?P<title>[A-Z][A-Za-z0-9 ,;:'\"()/&\-]{1,120})$"
)

_EXHIBIT_HEADING_RE = re.compile(
    r"^(EXHIBIT|APPENDIX|ANNEXURE|ANNEX|SCHEDULE)\s+([A-Za-z0-9]+)\b[:\-]?\s*(.*)$",
    re.IGNORECASE,
)


@dataclass
class Line:
    text: str
    page: int


@dataclass
class TableAnchor:
    after_line_index: int
    table: TableModel


@dataclass
class _PendingClause:
    section_number: str | None
    heading: str | None
    level: int
    page_start: int
    text_parts: list[str] = field(default_factory=list)
    page_end: int = 0
    table_ids: list[str] = field(default_factory=list)


def parse_heading(line: str) -> tuple[str, str, int] | None:
    """Returns (section_number, title, level) if `line` is a heading, else None."""
    stripped = line.strip()
    if not stripped or len(stripped) > 160:
        return None

    m = _HEADING_RE.match(stripped)
    if m:
        num = m.group("num")
        level = num.count(".") + 1
        return num, m.group("title").strip(), level

    m2 = _EXHIBIT_HEADING_RE.match(stripped)
    if m2:
        label = f"{m2.group(1).title()} {m2.group(2).upper()}"
        title = m2.group(3).strip() or label
        return label, title, 1

    return None


def parent_of(section_number: str) -> str | None:
    """'4.2.1' -> '4.2'; '4' -> None. Non-numeric (exhibit) labels have no parent."""
    if "." not in section_number:
        return None
    return section_number.rsplit(".", 1)[0]


def build_document(
    doc_id: str,
    filename: str,
    doc_type: DocType,
    lines: list[Line],
    table_anchors: list[TableAnchor],
    page_count: int,
) -> ParsedDocument:
    anchors_by_index: dict[int, list[TableModel]] = {}
    for anchor in table_anchors:
        anchors_by_index.setdefault(anchor.after_line_index, []).append(anchor.table)

    pending: list[_PendingClause] = []
    finished: list[_PendingClause] = []

    # An implicit "preamble" clause captures any text before the first heading.
    preamble = _PendingClause(section_number=None, heading="Preamble", level=0, page_start=lines[0].page if lines else 1)
    pending.append(preamble)

    def close_to_level(new_level: int):
        """Pop pending clauses deeper than or equal to the incoming heading's level."""
        while pending and pending[-1].level >= new_level and pending[-1] is not preamble:
            finished.append(pending.pop())

    all_tables: list[TableModel] = []

    for idx, line in enumerate(lines):
        parsed = parse_heading(line.text)
        if parsed:
            num, title, level = parsed
            close_to_level(level)
            clause = _PendingClause(section_number=num, heading=title, level=level, page_start=line.page)
            pending.append(clause)
        else:
            if pending:
                pending[-1].text_parts.append(line.text)
            pending[-1].page_end = line.page if pending else 1

        for table in anchors_by_index.get(idx, []):
            all_tables.append(table)
            if pending:
                pending[-1].table_ids.append(table.id)
                pending[-1].text_parts.append(f"[TABLE:{table.id}]")

    while pending:
        finished.append(pending.pop())

    # keep only clauses that carry a heading (drop empty preamble if it has no content)
    clauses: list[Clause] = []
    for pc in finished:
        if pc.heading == "Preamble" and not pc.text_parts:
            continue
        text = "\n".join(pc.text_parts).strip()
        section_id = pc.section_number or "preamble"
        clause_id = f"{doc_id}::{section_id}"
        references, general_override = extract_references(text)
        clause = Clause(
            id=clause_id,
            doc_id=doc_id,
            doc_type=doc_type,
            section_number=pc.section_number,
            parent_section=parent_of(pc.section_number) if pc.section_number else None,
            level=pc.level,
            heading=pc.heading,
            text=text,
            page_start=pc.page_start,
            page_end=max(pc.page_end, pc.page_start),
            references=references,
            table_ids=pc.table_ids,
        )
        clauses.append(clause)

    # restore document order (finished was built by popping, i.e. reverse-ish order per branch)
    clauses.sort(key=lambda c: (c.page_start, _sort_key(c.section_number)))

    known_exhibits = sorted(
        {
            r.target_label
            for c in clauses
            for r in c.references
            if r.type.value in ("exhibit", "appendix", "annexure", "schedule") and r.target_label
        }
    )

    return ParsedDocument(
        doc_id=doc_id,
        filename=filename,
        doc_type=doc_type,
        clauses=clauses,
        tables=all_tables,
        page_count=page_count,
        known_exhibit_labels=known_exhibits,
        available_exhibit_labels=[],
    )


def _sort_key(section_number: str | None):
    if not section_number:
        return (-1,)
    if not re.match(r"^\d+(\.\d+)*$", section_number):
        # exhibit-style labels sort after numeric sections
        return (10_000, section_number)
    return tuple(int(p) for p in section_number.split("."))
