"""Models for Chat with Contract (RAG-based Q&A over an MSA/SOW pair)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field
# Testing pull request workflow

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatCitation(BaseModel):
    clause_id: str
    doc_id: str
    section_number: str | None = None
    heading: str | None = None


class ChatRequest(BaseModel):
    doc_ids: list[str]
    question: str
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    citations: list[ChatCitation] = Field(default_factory=list)
