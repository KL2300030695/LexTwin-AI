"""Chat with Contract: retrieval is local and deterministic (embeddings +
FAISS, app/rag/) -- no AI provider call happens during retrieval itself.
Only the final step, turning retrieved clauses into a grounded natural-
language answer, calls the configured AI provider (app/services/ai_client.py).
This mirrors the rest of the project's philosophy: deterministic wherever
a judgment call isn't actually required, LLM only where one genuinely is.
"""
from __future__ import annotations

import re

from app.models.chat import ChatCitation, ChatMessage, ChatResponse
from app.models.schema import Clause
from app.rag.embedder import embed_query
from app.rag.index import ClauseIndex, build_clause_index, search_clause_index
from app.services.ai_client import answer_chat_question
from app.services.document_service import get_document

_TOP_K = 8

# The prompt tells the model not to inline bracketed reference markers like
# "[1]" in the answer text (citations are rendered separately as chips) --
# this strips any that slip through anyway, since prompt compliance isn't
# guaranteed on every call.
_INLINE_REF_MARKER_RE = re.compile(r"\s?\[\d+\]")

# In-process cache only -- matches the singleton pattern already used for the
# AI provider clients. Rebuilt if the document set's clause count changes
# (e.g. a document was re-uploaded), not persisted across restarts.
_index_cache: dict[tuple[str, ...], ClauseIndex] = {}


def _get_or_build_index(doc_ids: list[str], clauses: list[Clause]) -> ClauseIndex:
    key = tuple(sorted(doc_ids))
    cached = _index_cache.get(key)
    if cached is not None and len(cached.clauses) == len(clauses):
        return cached
    index = build_clause_index(clauses)
    _index_cache[key] = index
    return index


def _build_context_block(retrieved: list[tuple[Clause, float]]) -> str:
    lines = []
    for i, (clause, _score) in enumerate(retrieved, start=1):
        heading = f' "{clause.heading}"' if clause.heading else ""
        lines.append(f"[{i}] {clause.doc_type.value} §{clause.section_number}{heading}: {clause.text}")
    return "\n\n".join(lines)


def answer_question(doc_ids: list[str], question: str, history: list[ChatMessage]) -> ChatResponse:
    documents = []
    for doc_id in doc_ids:
        doc = get_document(doc_id)
        if doc is None:
            raise ValueError(f"Document not found: {doc_id}")
        documents.append(doc)

    clauses = [c for doc in documents for c in doc.clauses if c.section_number and c.text]
    if not clauses:
        return ChatResponse(answer="No analyzable clauses were found in the selected documents.", citations=[])

    index = _get_or_build_index(doc_ids, clauses)
    query_embedding = embed_query(question)
    retrieved = search_clause_index(index, query_embedding, top_k=_TOP_K)

    context_block = _build_context_block(retrieved)
    history_block = "\n".join(f"{m.role}: {m.content}" for m in history)

    chat_answer = answer_chat_question(context_block, history_block, question)

    citations: list[ChatCitation] = []
    for ref in chat_answer.cited_refs:
        if 1 <= ref <= len(retrieved):
            clause, _ = retrieved[ref - 1]
            citations.append(
                ChatCitation(
                    clause_id=clause.id,
                    doc_id=clause.doc_id,
                    section_number=clause.section_number,
                    heading=clause.heading,
                )
            )

    cleaned_answer = _INLINE_REF_MARKER_RE.sub("", chat_answer.answer)
    return ChatResponse(answer=cleaned_answer, citations=citations)
