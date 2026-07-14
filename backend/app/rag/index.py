"""In-memory FAISS vector index over a document pair's clauses, for the RAG
chat feature. Documents in this app are small (tens of clauses), so building
an index on demand is cheap -- app/services/chat_service.py caches one per
(doc_ids) key to avoid re-embedding on every message within a session, but
there's no persistence across process restarts (matches the in-process
singleton pattern already used for the AI provider clients).
"""
from __future__ import annotations

from dataclasses import dataclass

import faiss
import numpy as np

from app.models.schema import Clause
from app.rag.embedder import embed_passages


@dataclass
class ClauseIndex:
    index: faiss.IndexFlatIP
    clauses: list[Clause]


def build_clause_index(clauses: list[Clause]) -> ClauseIndex:
    # Heading carries useful topical signal for short/generic clause bodies
    # (e.g. "Invoicing and Payment"), so fold it into the embedded text.
    texts = [f"{c.heading}. {c.text}" if c.heading else c.text for c in clauses]
    embeddings = embed_passages(texts)
    dimension = embeddings.shape[1] if embeddings.size else 1024
    index = faiss.IndexFlatIP(dimension)
    if embeddings.size:
        index.add(embeddings)
    return ClauseIndex(index=index, clauses=clauses)


def search_clause_index(clause_index: ClauseIndex, query_embedding: np.ndarray, top_k: int = 6) -> list[tuple[Clause, float]]:
    if not clause_index.clauses:
        return []
    k = min(top_k, len(clause_index.clauses))
    scores, indices = clause_index.index.search(query_embedding.reshape(1, -1), k)
    return [(clause_index.clauses[i], float(scores[0][pos])) for pos, i in enumerate(indices[0]) if i != -1]
