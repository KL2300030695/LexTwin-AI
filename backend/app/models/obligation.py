"""Models for deterministic obligation extraction."""
from __future__ import annotations

from pydantic import BaseModel


class Obligation(BaseModel):
    id: str
    doc_id: str
    clause_id: str
    section_number: str | None = None
    heading: str | None = None
    text: str  # the sentence containing the obligation
    responsible_party: str | None = None  # best-effort; not a resolved legal party
    obligation_verb: str  # the matched modal phrase, e.g. "shall", "must", "agrees to"
    deadline_text: str | None = None  # raw matched deadline phrase, e.g. "within forty-five days"
    deadline_days: int | None = None  # normalized day count, when the deadline is a relative day count
    page: int
