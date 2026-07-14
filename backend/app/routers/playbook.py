from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.models.playbook import TopicRule
from app.playbook import list_all_categories
from app.playbook.topic_rules import get_topic_rules, reset_topic_rules, save_topic_rules

router = APIRouter()


class TopicRulesUpdate(BaseModel):
    topics: list[TopicRule]


@router.get("/topics", response_model=list[TopicRule])
def get_topics():
    return get_topic_rules()


@router.put("/topics", response_model=list[TopicRule])
def put_topics(payload: TopicRulesUpdate):
    return save_topic_rules(payload.topics)


@router.post("/topics/reset", response_model=list[TopicRule])
def reset_topics():
    return reset_topic_rules()


@router.get("/categories")
def get_reference_categories():
    """Reference clause categories pooled from every generated playbook
    (CUAD, LEDGAR, Unfair ToS, ContractNLI -- see app/playbook/__init__.py)
    -- inspiration for adding new playbook topics, not the live config itself."""
    return [
        {
            "source": c["source"],
            "category": c["category"],
            "example_clauses": c.get("example_clauses", [])[:2],
            **({"hypothesis": c["hypothesis"]} if "hypothesis" in c else {}),
        }
        for c in list_all_categories()
    ]
