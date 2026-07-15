"""Deterministic (non-LLM) clause topic alignment.

'Align clauses covering the same topic (payment terms, liability,
termination, etc.)' -- this is a structural/keyword matching problem, not a
reasoning problem, so it's solved with regexes over clause headings rather
than an LLM call. The local model is reserved for the actual contradiction
judgment (see app/services/local_llm_client.py), consistent with using the
LLM only for what can't be done deterministically.

The topic taxonomy itself is the configurable legal playbook
(app/playbook/topic_rules.py) -- editable via /api/playbook/topics rather
than hardcoded here, so a legal team can add/adjust which topics get
compared without a code change.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.schema import Clause, ParsedDocument
from app.models.playbook import TopicRule
from app.playbook.topic_rules import get_topic_rules

CompiledRules = dict[str, list[re.Pattern]]


def _compile_rules(rules: list[TopicRule]) -> CompiledRules:
    return {rule.topic: [re.compile(p, re.I) for p in rule.patterns] for rule in rules}


def classify_topic(heading: str | None, compiled: CompiledRules | None = None) -> str | None:
    """Maps a clause heading to one of the configured topics, or None.

    Patterns are matched against the clause heading only (not body text) --
    headings in a well-structured MSA/SOW are reliably descriptive, and
    restricting to headings avoids false positives from body text that
    merely mentions another topic in passing.
    """
    if not heading:
        return None
    compiled = compiled if compiled is not None else _compile_rules(get_topic_rules())
    for topic, patterns in compiled.items():
        if any(p.search(heading) for p in patterns):
            return topic
    return None


def _first_topic_match_per_clause(clauses: list[Clause], compiled: CompiledRules) -> dict[str, Clause]:
    """First clause (in document order) matching each topic, skipping clauses
    with no body text (bare section headers that only introduce sub-clauses
    carry no content worth comparing)."""
    matches: dict[str, Clause] = {}
    for clause in clauses:
        if not clause.text or not clause.text.strip():
            continue
        topic = classify_topic(clause.heading, compiled)
        if topic and topic not in matches:
            matches[topic] = clause
    return matches


@dataclass
class ClausePairCandidate:
    topic: str
    msa_clause: Clause
    sow_clause: Clause


def align_clauses(msa: ParsedDocument, sow: ParsedDocument) -> list[ClausePairCandidate]:
    """Returns one candidate pair per topic present (with non-empty text) in
    both documents, using the currently configured playbook topics."""
    compiled = _compile_rules(get_topic_rules())
    msa_topics = _first_topic_match_per_clause(msa.clauses, compiled)
    sow_topics = _first_topic_match_per_clause(sow.clauses, compiled)
    shared = sorted(set(msa_topics) & set(sow_topics))
    return [
        ClausePairCandidate(topic=topic, msa_clause=msa_topics[topic], sow_clause=sow_topics[topic])
        for topic in shared
    ]
