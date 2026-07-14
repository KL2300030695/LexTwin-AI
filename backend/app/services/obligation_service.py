from __future__ import annotations

from app.models.obligation import Obligation
from app.obligations.extractor import extract_obligations
from app.services.document_service import get_document


def extract_obligations_for_docs(doc_ids: list[str]) -> list[Obligation]:
    obligations: list[Obligation] = []
    for doc_id in doc_ids:
        doc = get_document(doc_id)
        if doc is None:
            raise ValueError(f"Document not found: {doc_id}")
        obligations.extend(extract_obligations(doc))
    obligations.sort(key=lambda o: (o.deadline_days is None, o.deadline_days if o.deadline_days is not None else 0))
    return obligations
