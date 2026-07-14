from __future__ import annotations

from app.completeness import check_completeness
from app.models.completeness import CompletenessAnalysis
from app.services.document_service import get_document


def check_completeness_for_docs(doc_ids: list[str]) -> CompletenessAnalysis:
    documents = []
    for doc_id in doc_ids:
        doc = get_document(doc_id)
        if doc is None:
            raise ValueError(f"Document not found: {doc_id}")
        documents.append(doc)
    return check_completeness(documents)
