"""Storage-backed, editable topic taxonomy for cross-document contradiction
alignment -- the 'configurable legal playbook' referenced in the problem
statement. Persisted through the same get_store() abstraction as everything
else (Firestore in production, local JSON in dev), so edits made via the API
survive restarts and are consistent with the rest of the app's persistence.

Falls back to a curated default set (the same taxonomy Phase 5 originally
shipped with, hardcoded) until a user saves their own configuration.
"""
from __future__ import annotations

from app.firebase import get_store
from app.models.playbook import TopicRule, TopicRulesConfig

COLLECTION = "playbook_config"
DOC_ID = "topic_rules"

DEFAULT_TOPICS: list[TopicRule] = [
    TopicRule(topic="Payment Terms", patterns=[r"\binvoic", r"\bpayment terms\b"]),
    TopicRule(topic="Termination", patterns=[r"\btermin"]),
    TopicRule(topic="Liability", patterns=[r"\bliabilit"]),
    TopicRule(topic="Indemnification", patterns=[r"\bindemnif"]),
    TopicRule(topic="Confidentiality", patterns=[r"\bconfidential"]),
    TopicRule(topic="Intellectual Property", patterns=[r"\bintellectual property\b", r"\bip\b"]),
    TopicRule(topic="Service Levels", patterns=[r"\bservice level", r"\bslas?\b", r"\buptime\b"]),
    TopicRule(topic="Governing Law", patterns=[r"\bgoverning law\b"]),
    TopicRule(topic="Insurance", patterns=[r"\binsurance\b"]),
    TopicRule(topic="Assignment", patterns=[r"\bassignment\b"]),
    TopicRule(topic="Audit Rights", patterns=[r"\baudit\b"]),
    TopicRule(topic="Warranty", patterns=[r"\bwarrant"]),
    TopicRule(topic="Non-Compete / Exclusivity", patterns=[r"\bnon-compete\b", r"\bexclusiv"]),
    TopicRule(topic="Dispute Resolution", patterns=[r"\bdispute\b"]),
    TopicRule(topic="Change Management", patterns=[r"\bchange (order|management)\b"]),
]


def get_topic_rules() -> list[TopicRule]:
    store = get_store()
    data = store.get(COLLECTION, DOC_ID)
    if data is None:
        return list(DEFAULT_TOPICS)
    return TopicRulesConfig.model_validate(data).topics


def save_topic_rules(topics: list[TopicRule]) -> list[TopicRule]:
    store = get_store()
    store.save(COLLECTION, DOC_ID, TopicRulesConfig(topics=topics).model_dump(mode="json"))
    return topics


def reset_topic_rules() -> list[TopicRule]:
    store = get_store()
    store.delete(COLLECTION, DOC_ID)
    return list(DEFAULT_TOPICS)
