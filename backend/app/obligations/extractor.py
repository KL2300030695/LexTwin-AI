"""Deterministic (non-LLM) obligation extraction.

'Parse contracts and SOWs into ... obligations.' Finds sentences containing
an obligation-indicating modal ('shall', 'must', 'agrees to', ...) -- as
opposed to permissive language ('may') -- and best-effort extracts the
responsible party and any stated deadline. Regex/rule-based by design,
consistent with reserving the LLM for judgment tasks (Phase 5 contradiction
detection, Phase 6 redlining) and using deterministic code for structural
extraction (parsing, graph building, completeness checking).

This is intentionally a heuristic, not an NLP pipeline: it will miss
deadlines phrased in ways the patterns below don't cover, and the
"responsible party" is a best-effort guess at the subject phrase immediately
preceding the modal verb, not a resolved legal party. Good enough to build a
timeline view from real contract prose without a new hard dependency.
"""
from __future__ import annotations

import re

from app.models.obligation import Obligation
from app.models.schema import ParsedDocument

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")

# "may" is deliberately excluded -- it's a right/option, not an obligation.
_MODAL_RE = re.compile(r"\b(shall|must|will|agrees to|is required to|is obligated to)\b", re.I)

_DEADLINE_RE = re.compile(
    r"\b(?:within|no later than|not later than|have)\s+([a-z\-]+|\d+)\s+(?:calendar\s+|business\s+)?days?\b",
    re.I,
)

_ONES = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}


def _word_to_number(word: str) -> int | None:
    word = word.lower().strip()
    if word.isdigit():
        return int(word)
    if word in _ONES:
        return _ONES[word]
    if word in _TENS:
        return _TENS[word]
    if "-" in word:
        parts = word.split("-")
        if len(parts) == 2 and parts[0] in _TENS and parts[1] in _ONES:
            return _TENS[parts[0]] + _ONES[parts[1]]
    return None


def _split_sentences(text: str) -> list[str]:
    normalized = " ".join(text.split())  # collapse whitespace, including PDF line-wrap newlines
    if not normalized:
        return []
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(normalized) if s.strip()]


def _extract_responsible_party(sentence: str, modal_start: int) -> str | None:
    prefix = sentence[:modal_start].strip()
    if not prefix:
        return None
    words = prefix.split()
    party = " ".join(words[-4:]).strip(",;: ")
    return party or None


def _extract_deadline(sentence: str) -> tuple[str | None, int | None]:
    match = _DEADLINE_RE.search(sentence)
    if not match:
        return None, None
    return match.group(0), _word_to_number(match.group(1))


def extract_obligations(doc: ParsedDocument) -> list[Obligation]:
    obligations: list[Obligation] = []
    for clause in doc.clauses:
        if not clause.section_number or not clause.text:
            continue
        clause_counter = 0
        for sentence in _split_sentences(clause.text):
            modal_match = _MODAL_RE.search(sentence)
            if not modal_match:
                continue
            clause_counter += 1
            deadline_text, deadline_days = _extract_deadline(sentence)
            obligations.append(
                Obligation(
                    id=f"{clause.id}-obl-{clause_counter}",
                    doc_id=doc.doc_id,
                    clause_id=clause.id,
                    section_number=clause.section_number,
                    heading=clause.heading,
                    text=sentence,
                    responsible_party=_extract_responsible_party(sentence, modal_match.start()),
                    obligation_verb=modal_match.group(0),
                    deadline_text=deadline_text,
                    deadline_days=deadline_days,
                    page=clause.page_start,
                )
            )
    return obligations
