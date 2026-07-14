"""Models for the configurable legal playbook -- the topic taxonomy that
Phase 5 (cross-document contradiction detection) uses to align MSA and SOW
clauses covering the same subject."""
from __future__ import annotations

from pydantic import BaseModel, Field


class TopicRule(BaseModel):
    topic: str
    # Regex patterns (case-insensitive) matched against a clause heading.
    # A clause is classified under this topic if any pattern matches.
    patterns: list[str] = Field(default_factory=list)


class TopicRulesConfig(BaseModel):
    topics: list[TopicRule] = Field(default_factory=list)
