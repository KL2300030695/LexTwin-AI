"""Regression test for a race condition in get_store(): FastAPI runs sync
endpoints in a thread pool, so several requests can reach the "not yet
initialized" check at the same instant (e.g. a workspace page's parallel
API calls right after a fresh backend start). Without a lock, two threads
could both pass the `_store is None` check before either finished
initializing -- on the real Firestore path this raised "the default
Firebase app already exists"; this test exercises the same lock/double-check
logic via the local-store path (always used in tests, see conftest.py),
which doesn't require real credentials but does verify the invariant the
fix establishes: concurrent callers never create more than one store.
"""
import threading

from app.firebase import get_store


def test_concurrent_get_store_calls_return_the_same_instance():
    results: list[object] = []
    errors: list[Exception] = []
    start_barrier = threading.Barrier(20)

    def call_get_store():
        start_barrier.wait()  # maximize the chance all threads race the check at once
        try:
            results.append(get_store())
        except Exception as e:  # noqa: BLE001 -- capturing any race-condition failure
            errors.append(e)

    threads = [threading.Thread(target=call_get_store) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert len(results) == 20
    assert len({id(r) for r in results}) == 1
