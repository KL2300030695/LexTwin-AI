"""Tests the FAISS clause index (app/rag/index.py) against the real
embedding model -- marked slow for the same reason as test_embedder.py."""
import pytest

from app.models.schema import Clause, DocType
from app.rag.embedder import embed_query
from app.rag.index import build_clause_index, search_clause_index

pytestmark = pytest.mark.slow


def _clause(section_number: str, heading: str, text: str, doc_id: str = "d1") -> Clause:
    return Clause(
        id=f"{doc_id}::{section_number}", doc_id=doc_id, doc_type=DocType.MSA, section_number=section_number,
        parent_section=None, level=1, heading=heading, text=text, page_start=1, page_end=1,
    )


def test_search_returns_the_most_relevant_clause_first():
    clauses = [
        _clause("5.1", "Invoicing and Payment", "Client shall pay all undisputed invoices within forty-five days of receipt."),
        _clause("7.1", "Confidentiality", "Each party shall protect the other party's Confidential Information."),
        _clause("1.1", "Scope of Services", "Provider will migrate Client's workloads to a cloud environment."),
    ]
    index = build_clause_index(clauses)
    query_embedding = embed_query("What is the payment deadline?")
    results = search_clause_index(index, query_embedding, top_k=2)

    assert len(results) == 2
    top_clause, _score = results[0]
    assert top_clause.section_number == "5.1"


def test_search_respects_top_k():
    clauses = [_clause(str(i), f"Clause {i}", f"This is clause number {i} about topic {i}.") for i in range(10)]
    index = build_clause_index(clauses)
    query_embedding = embed_query("clause number 5")
    results = search_clause_index(index, query_embedding, top_k=3)
    assert len(results) == 3


def test_search_on_empty_index_returns_empty_list():
    index = build_clause_index([])
    query_embedding = embed_query("anything")
    results = search_clause_index(index, query_embedding, top_k=5)
    assert results == []
