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
    r"^(?P<num>\d+(?:\.\d+){0,4})\.?\s+(?P<title>[A-Z\"'][A-Za-z0-9 ,;:'\"()/&\-]{1,120})$"
)

_EXHIBIT_HEADING_RE = re.compile(
    r"^(EXHIBIT|APPENDIX|ANNEXURE|ANNEX|SCHEDULE)\s+([A-Za-z0-9]+)\b[:\-]?\s*(.*)$",
    re.IGNORECASE,
)

# Fallback for the common real-world drafting style where the heading and the
# clause body run together in one paragraph, e.g.:
#   "1. Website Design and Development. Client agrees to pay Company..."
# instead of the heading being on its own line. Only tried when _HEADING_RE
# doesn't match. The title must be a short run of Capitalized/connector words
# ending at a literal period -- this keeps it from misreading an ordinary
# sentence that happens to start with a number as a heading.
_INLINE_WORD = r"(?:[A-Z][A-Za-z']*|and|of|or|the|to|for|in|on|with|by)"
_INLINE_TITLE = rf"{_INLINE_WORD}(?:\s+{_INLINE_WORD}){{0,5}}"
_INLINE_HEADING_RE = re.compile(
    rf"^(?P<num>\d+(?:\.\d+){{0,4}})\.\s+(?P<title>{_INLINE_TITLE})\.\s+(?P<rest>.{{10,}})$"
)


@dataclass
class Line:
    text: str
    page: int
    # False for a wrapped continuation line within the same source paragraph/
    # text block -- only the first line of a block is ever a heading candidate,
    # so a wrapped body line that happens to start with e.g. "Schedule ..."
    # can't be mistaken for a real "Schedule X" heading.
    is_block_start: bool = True


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


def parse_inline_heading(line: str) -> tuple[str, str, int, str] | None:
    """Returns (section_number, title, level, remaining_body_text) if `line`
    is a heading+body-on-one-line paragraph (see _INLINE_HEADING_RE), else None.
    """
    stripped = line.strip()
    if not stripped or len(stripped) > 500:
        return None
    m = _INLINE_HEADING_RE.match(stripped)
    if not m:
        return None
    num = m.group("num")
    level = num.count(".") + 1
    return num, m.group("title").strip(), level, m.group("rest").strip()


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

    # Tables that appeared before any text line at all (rare: doc/page opens with a table).
    for table in anchors_by_index.get(-1, []):
        all_tables.append(table)
        if pending:
            pending[-1].table_ids.append(table.id)

    for idx, line in enumerate(lines):
        parsed = parse_heading(line.text) if line.is_block_start else None
        # Unlike _HEADING_RE, the inline-heading pattern is checked on every
        # line (not just block starts): real contracts often pack multiple
        # numbered clauses into a single visual block with no blank-line gap,
        # so "2. Payment Terms. Upon signing..." can start mid-block. Its
        # stricter shape (digit + short Title-Case phrase + period) makes
        # false positives on ordinary wrapped body text unlikely.
        inline = parse_inline_heading(line.text) if not parsed else None
        if parsed:
            num, title, level = parsed
            close_to_level(level)
            clause = _PendingClause(section_number=num, heading=title, level=level, page_start=line.page)
            pending.append(clause)
        elif inline:
            num, title, level, rest = inline
            close_to_level(level)
            clause = _PendingClause(section_number=num, heading=title, level=level, page_start=line.page)
            clause.text_parts.append(rest)
            pending.append(clause)
        else:
            if pending:
                pending[-1].text_parts.append(line.text)
            pending[-1].page_end = line.page if pending else 1

        for table in anchors_by_index.get(idx, []):
            all_tables.append(table)
            if pending:
                pending[-1].table_ids.append(table.id)

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
            has_general_override=general_override,
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

    # A clause whose own heading IS an exhibit/appendix/etc. (e.g. this doc
    # contains "EXHIBIT B" as a section) means that exhibit's content is present.
    available_exhibits = sorted(
        {
            c.section_number
            for c in clauses
            if c.section_number and not re.match(r"^\d+(\.\d+)*$", c.section_number)
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
        available_exhibit_labels=available_exhibits,
    )


def _sort_key(section_number: str | None):
    if not section_number:
        return (-1,)
    if not re.match(r"^\d+(\.\d+)*$", section_number):
        # exhibit-style labels sort after numeric sections
        return (10_000, section_number)
    return tuple(int(p) for p in section_number.split("."))
