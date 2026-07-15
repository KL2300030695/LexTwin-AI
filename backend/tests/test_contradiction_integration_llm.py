"""Live smoke test against the real local model (downloads/loads the actual
GGUF model, real inference) and real sample contracts.

No API key and no cost -- everything runs on-machine -- but real inference
is slow (a multi-second-to-minute model load plus real generation time), so
this is marked `slow` like the embedding model tests and excluded from the
default run (see pytest.ini). Run explicitly:
    pytest -m slow tests/test_contradiction_integration_llm.py
"""
from pathlib import Path

import pytest

from app.models.contradiction import ContradictionStatus
from app.parsers import parse_document
from app.models.schema import DocType
from app.services import contradiction_service

SAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "samples"
MSA_PATH = SAMPLES_DIR / "msa_sample.pdf"
SOW_PATH = SAMPLES_DIR / "sow_sample.pdf"

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not (MSA_PATH.exists() and SOW_PATH.exists()),
        reason="Sample PDFs not generated yet -- run `python scripts/generate_samples.py`",
    ),
]


def test_local_model_detects_seeded_payment_contradiction(monkeypatch):
    msa = parse_document(str(MSA_PATH), "msa-llm-test", "msa_sample.pdf", DocType.MSA)
    sow = parse_document(str(SOW_PATH), "sow-llm-test", "sow_sample.pdf", DocType.SOW)
    docs = {"msa-llm-test": msa, "sow-llm-test": sow}
    monkeypatch.setattr(contradiction_service, "get_document", lambda doc_id: docs.get(doc_id))

    result = contradiction_service.analyze_contradictions("msa-llm-test", "sow-llm-test")

    payment_result = next(r for r in result.results if r.topic == "Payment Terms")
    assert payment_result.status == ContradictionStatus.ANALYZED
    assert payment_result.has_contradiction is True
    assert payment_result.confidence is not None and payment_result.confidence > 0.5
    assert payment_result.explanation

    service_levels_result = next(r for r in result.results if r.topic == "Service Levels")
    assert service_levels_result.status == ContradictionStatus.ANALYZED
