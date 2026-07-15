"""Regression test for a concurrency bug in app/rag/embedder.py: FastAPI runs
sync endpoints in a thread pool, so concurrent Chat with Contract requests
can reach this module concurrently. Without a lock, two threads could both
construct a SentenceTransformer at once, or both call .encode() on it
concurrently -- the same class of bug already found and fixed in
local_llm_client.py and app/firebase.py, and verified here to have caused a
real backend crash under concurrent chat usage.

Uses a fake stand-in for SentenceTransformer since downloading/running the
real ~1.3GB model isn't practical in a fast unit test -- see
test_embedder.py (marked slow) for tests against the real model.
"""
import threading
import time

import numpy as np

import app.rag.embedder as embedder


class _FakeSentenceTransformer:
    _construction_count = 0
    _construction_lock = threading.Lock()

    def __init__(self, *args, **kwargs):
        with self._construction_lock:
            _FakeSentenceTransformer._construction_count += 1
        self._in_flight = 0
        self.max_concurrent_encodes = 0
        self._state_lock = threading.Lock()

    def encode(self, texts, **kwargs):
        with self._state_lock:
            self._in_flight += 1
            self.max_concurrent_encodes = max(self.max_concurrent_encodes, self._in_flight)
        time.sleep(0.05)
        with self._state_lock:
            self._in_flight -= 1
        return np.zeros((len(texts), 1024), dtype="float32")


def test_concurrent_model_construction_happens_once(monkeypatch):
    monkeypatch.setattr(embedder, "_model", None)
    monkeypatch.setattr(embedder, "SentenceTransformer", _FakeSentenceTransformer)
    _FakeSentenceTransformer._construction_count = 0

    threads = [threading.Thread(target=embedder._get_model) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert _FakeSentenceTransformer._construction_count == 1


def test_concurrent_encode_calls_are_serialized(monkeypatch):
    monkeypatch.setattr(embedder, "_model", None)
    monkeypatch.setattr(embedder, "SentenceTransformer", _FakeSentenceTransformer)

    threads = [threading.Thread(target=embedder.embed_passages, args=(["clause text"],)) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert embedder._model.max_concurrent_encodes == 1
