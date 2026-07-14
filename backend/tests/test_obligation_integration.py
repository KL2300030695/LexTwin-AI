"""Runs deterministic obligation extraction against the real synthetic MSA +
SOW samples to confirm the seeded payment/review deadlines are correctly
found and normalized."""
from pathlib import Path

import pytest

from app.models.schema import DocType
from app.obligations.extractor import extract_obligations
from app.parsers import parse_document

SAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "samples"
MSA_PATH = SAMPLES_DIR / "msa_sample.pdf"
SOW_PATH = SAMPLES_DIR / "sow_sample.pdf"

pytestmark = pytest.mark.skipif(
    not (MSA_PATH.exists() and SOW_PATH.exists()),
    reason="Sample PDFs not generated yet -- run `python scripts/generate_samples.py`",
)


@pytest.fixture(scope="module")
def msa():
    return parse_document(str(MSA_PATH), "msa-test", "msa_sample.pdf", DocType.MSA)


@pytest.fixture(scope="module")
def sow():
    return parse_document(str(SOW_PATH), "sow-test", "sow_sample.pdf", DocType.SOW)


def _for_section(obligations, section_number):
    return [o for o in obligations if o.section_number == section_number]


def test_msa_payment_obligation_deadline_extracted(msa):
    obligations = extract_obligations(msa)
    matches = [o for o in _for_section(obligations, "5.1") if o.deadline_days is not None]
    assert len(matches) == 1
    assert matches[0].deadline_days == 45
    assert "Client" in (matches[0].responsible_party or "")


def test_sow_payment_obligation_deadline_extracted(sow):
    obligations = extract_obligations(sow)
    matches = [o for o in _for_section(obligations, "3.3") if o.deadline_days is not None]
    assert len(matches) == 1
    assert matches[0].deadline_days == 15


def test_sow_review_obligation_deadline_extracted(sow):
    obligations = extract_obligations(sow)
    matches = _for_section(obligations, "7.1")
    assert len(matches) == 1
    assert matches[0].deadline_days == 10


def test_permissive_termination_clauses_produce_no_obligations(msa):
    """MSA termination language uses 'may' ('Either party may terminate...')
    -- must not be picked up as an obligation."""
    obligations = extract_obligations(msa)
    assert not any("may terminate" in o.text.lower() for o in obligations)


def test_every_obligation_has_a_modal_verb_and_source_clause(msa, sow):
    for doc in (msa, sow):
        for obligation in extract_obligations(doc):
            assert obligation.obligation_verb
            assert obligation.clause_id
            assert obligation.doc_id == doc.doc_id
