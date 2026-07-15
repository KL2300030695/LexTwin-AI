"""Regression test for a concurrency bug in chat_service.py's
_get_or_build_index(): FastAPI runs sync endpoints in a thread pool, so two
concurrent Chat with Contract requests for the same (or first-ever) document
pair could both see "not cached" and both call build_clause_index() at once
-- itself racing on the embedder's model singleton (see
test_embedder_concurrency.py). Verified this class of bug caused a real
backend crash under concurrent chat usage; _index_cache_lock serializes the
whole check-build-store sequence.
"""
import threading
import time
from unittest.mock import patch

import app.services.chat_service as chat_service
from app.models.schema import Clause, DocType
from app.rag.index import ClauseIndex


def _clause(section_number: str, doc_id: str = "d1") -> Clause:
    return Clause(
        id=f"{doc_id}::{section_number}", doc_id=doc_id, doc_type=DocType.MSA, section_number=section_number,
        parent_section=None, level=1, heading="Heading", text="Some clause text.", page_start=1, page_end=1,
    )


def test_concurrent_index_builds_for_the_same_doc_ids_happen_once():
    chat_service._index_cache.clear()
    clauses = [_clause("5.1")]
    build_call_count = 0
    build_lock = threading.Lock()

    def fake_build_clause_index(clauses):
        nonlocal build_call_count
        with build_lock:
            build_call_count += 1
        time.sleep(0.05)  # hold long enough for a race to surface
        return ClauseIndex(index=None, clauses=clauses)

    with patch("app.services.chat_service.build_clause_index", side_effect=fake_build_clause_index):
        threads = [
            threading.Thread(target=chat_service._get_or_build_index, args=(["d1"], clauses))
            for _ in range(20)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    assert build_call_count == 1
    chat_service._index_cache.clear()
