"""Regression test for a concurrency bug in local_llm_client.py: FastAPI runs
sync endpoints in a thread pool, so concurrent contradiction/redline/chat
requests can call into the same underlying Llama context at once. The
underlying llama.cpp context isn't safe for concurrent generation calls --
verified directly that two concurrent real inference calls reproducibly
crashed the whole backend process (a silent native crash, no Python
traceback), not just one request. `_llm_lock` in local_llm_client.py
serializes both model loading and every inference call through the shared
instance; this test exercises that lock with a mocked Llama object standing
in for the real model, since spinning up two truly concurrent real GGUF
inference calls isn't practical in a fast unit test.
"""
import threading
import time
from unittest.mock import patch

import app.services.local_llm_client as local_llm_client
from app.services.ai_schemas import ContradictionJudgment


class _FakeLlama:
    def __init__(self):
        self._in_flight = 0
        self.max_concurrent = 0
        self._state_lock = threading.Lock()

    def create_chat_completion(self, **kwargs):
        with self._state_lock:
            self._in_flight += 1
            self.max_concurrent = max(self.max_concurrent, self._in_flight)
        time.sleep(0.05)  # hold the "inference" long enough for a race to surface
        with self._state_lock:
            self._in_flight -= 1
        return {
            "choices": [
                {"message": {"content": '{"has_contradiction": false, "explanation": "x", "confidence": 0.5}'}}
            ]
        }


def test_concurrent_inference_calls_are_serialized():
    fake = _FakeLlama()
    with patch.object(local_llm_client, "_get_llm", return_value=fake):
        threads = [
            threading.Thread(
                target=local_llm_client._structured_chat_completion,
                args=("system prompt", "user content", ContradictionJudgment),
            )
            for _ in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    assert fake.max_concurrent == 1
