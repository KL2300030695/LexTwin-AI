"""Runs the completeness/refusal check against the real synthetic MSA + SOW
samples to confirm the seeded 'missing exhibit' issue surfaces correctly, and
that doc-set-aware resolution correctly clears the cross-document Exhibit A /
Section 4.2 references once both documents are analyzed together."""
from pathlib import Path

import pytest

from app.completeness import check_completeness
from app.models.schema import DocType
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


def _status_for(result, clause_id):
    return next(s for s in result.clause_statuses if s.clause_id == clause_id)


def test_msa_alone_flags_seeded_missing_exhibit_c(msa):
    result = check_completeness([msa])
    status = _status_for(result, "msa-test::4.3")
    assert status.can_evaluate is False
    assert any(m.label == "Exhibit C" for m in status.missing_references)


def test_msa_alone_exhibits_a_and_b_do_not_block_evaluation(msa):
    result = check_completeness([msa])
    status = _status_for(result, "msa-test::11.2")  # references Exhibit A and Exhibit B
    assert status.can_evaluate is True


def test_sow_alone_flags_msa_cross_references_as_missing(sow):
    """Without the MSA in scope, the SOW's references to Exhibit A (via the
    MSA) and Section 4.2 of the MSA must both be flagged."""
    result = check_completeness([sow])
    exhibit_status = _status_for(result, "sow-test::5.2")
    assert exhibit_status.can_evaluate is False

    sla_status = _status_for(result, "sow-test::4.1")
    assert sla_status.can_evaluate is False


def test_msa_and_sow_together_clear_cross_document_references(msa, sow):
    """With both documents in scope, the SOW's Exhibit A and Section 4.2
    cross-references resolve, but Exhibit C is still genuinely missing."""
    result = check_completeness([msa, sow])

    exhibit_status = _status_for(result, "sow-test::5.2")
    assert exhibit_status.can_evaluate is True

    sla_status = _status_for(result, "sow-test::4.1")
    assert sla_status.can_evaluate is True

    exhibit_c_status = _status_for(result, "msa-test::4.3")
    assert exhibit_c_status.can_evaluate is False
    assert result.blocked_clause_count == 1


def test_total_and_blocked_counts_are_consistent(msa, sow):
    result = check_completeness([msa, sow])
    assert result.total_clause_count == len(result.clause_statuses)
    actual_blocked = sum(1 for s in result.clause_statuses if not s.can_evaluate)
    assert actual_blocked == result.blocked_clause_count
