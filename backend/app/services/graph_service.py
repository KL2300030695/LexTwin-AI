from __future__ import annotations

from app.graph.dependency_graph import build_dependency_graph
from app.models.graph import GraphAnalysis
from app.services.document_service import get_document


def analyze_graph(doc_ids: list[str]) -> GraphAnalysis:
    documents = []
    for doc_id in doc_ids:
        doc = get_document(doc_id)
        if doc is None:
            raise ValueError(f"Document not found: {doc_id}")
        documents.append(doc)
    return build_dependency_graph(documents).analysis
