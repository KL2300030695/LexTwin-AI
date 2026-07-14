"""Integration tests against the real synthetic sample contracts used for the
demo (backend/scripts/generate_samples.py -> samples/msa_sample.pdf and
samples/sow_sample.pdf). These also serve as regression tests: if a future
change to the parser or to the sample generator breaks one of the three
intentionally-seeded issues (circular reference, missing exhibit, MSA/SOW
payment contradiction), a test here should fail.
"""
from pathlib import Path

import pytest

from app.models.schema import DocType, ReferenceType
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


def _clause(doc, section_number):
    return next(c for c in doc.clauses if c.section_number == section_number)


def test_msa_page_count(msa):
    assert msa.page_count == 6


def test_msa_full_hierarchy_present(msa):
    expected = {"1", "1.1", "1.2", "2", "2.1", "2.2", "2.3", "9", "9.1", "Exhibit A", "Exhibit B"}
    actual = {c.section_number for c in msa.clauses}
    assert expected.issubset(actual)


def test_msa_quoted_definition_headings_parsed(msa):
    c = _clause(msa, "1.1")
    assert c.heading == '"Confidential Information" Definition'
    assert c.parent_section == "1"


def test_msa_parent_child_relationships(msa):
    assert _clause(msa, "4.2").parent_section == "4"
    assert _clause(msa, "5.2").parent_section == "5"
    assert _clause(msa, "9.1").parent_section == "9"


def test_msa_notwithstanding_override_detected(msa):
    c = _clause(msa, "2.3")
    nw_refs = [r for r in c.references if r.is_notwithstanding]
    assert len(nw_refs) == 1
    assert nw_refs[0].target_section == "2.2"


def test_msa_seeded_circular_reference_pair_present(msa):
    """6.3 references 9.1 and 9.1 references 6.3 -- the intentional cycle."""
    c63 = _clause(msa, "6.3")
    c91 = _clause(msa, "9.1")
    assert "9.1" in {r.target_section for r in c63.references}
    assert "6.3" in {r.target_section for r in c91.references}


def test_msa_seeded_missing_exhibit_reference(msa):
    """4.3 references Exhibit C, which is never included in the doc set."""
    c = _clause(msa, "4.3")
    exhibit_refs = [r.target_label for r in c.references if r.type == ReferenceType.EXHIBIT]
    assert "Exhibit C" in exhibit_refs
    assert "Exhibit C" in msa.known_exhibit_labels
    assert "Exhibit C" not in msa.available_exhibit_labels


def test_msa_exhibits_a_and_b_are_available(msa):
    assert "Exhibit A" in msa.available_exhibit_labels
    assert "Exhibit B" in msa.available_exhibit_labels


def test_msa_payment_term_text_is_45_days(msa):
    c = _clause(msa, "5.1")
    assert "forty-five days" in c.text


def test_msa_tables_extracted_with_correct_row_counts(msa):
    assert len(msa.tables) == 3
    sla_table = next(t for t in msa.tables if t.rows[0][0] == "Uptime Tier")
    assert len(sla_table.rows) == 5  # header + 4 tiers
    penalty_table = next(t for t in msa.tables if t.rows[0][0] == "Days Past Due")
    assert len(penalty_table.rows) == 4  # header + 3 bands
    subcontractor_table = next(t for t in msa.tables if t.rows[0][0] == "Subcontractor")
    assert len(subcontractor_table.rows) == 3  # header + 2 subcontractors


def test_msa_tables_attached_to_correct_clause(msa):
    sla_table = next(t for t in msa.tables if t.rows[0][0] == "Uptime Tier")
    owning_clause = _clause(msa, "4.2")
    assert sla_table.id in owning_clause.table_ids


def test_sow_seeded_payment_contradiction_text(sow):
    """SOW says 15 days, MSA (see above) says 45 days -- the intentional contradiction
    that Phase 5 (LLM cross-document analysis) is meant to catch."""
    c = _clause(sow, "3.3")
    assert "fifteen days" in c.text


def test_sow_notwithstanding_override_detected(sow):
    c = _clause(sow, "7.2")
    nw_refs = [r for r in c.references if r.is_notwithstanding]
    assert len(nw_refs) == 1
    assert nw_refs[0].target_section == "6.1"


def test_sow_milestone_table_extracted(sow):
    milestone_table = next(t for t in sow.tables if t.rows[0][0] == "Milestone")
    assert len(milestone_table.rows) == 4
    assert milestone_table.rows[-1] == ["Post-Migration Validation Report accepted", "40%", "$100,000"]


def test_sow_references_exhibit_a_not_available_in_sow_alone(sow):
    """Exhibit A is only defined inside the MSA; from the SOW's own perspective
    it's referenced but not present -- this is exactly the case Phase 4's
    doc-set-aware (not single-doc) availability check needs to resolve."""
    assert "Exhibit A" in sow.known_exhibit_labels
    assert "Exhibit A" not in sow.available_exhibit_labels


def test_no_false_positive_headings_from_wrapped_table_or_body_text(msa, sow):
    """Regression guard for the 'Schedule described...' / mid-wrap false-heading
    bug found while building these fixtures."""
    bogus = {"Schedule DESCRIBED", "Schedule IN"}
    all_sections = {c.section_number for c in msa.clauses} | {c.section_number for c in sow.clauses}
    assert not (bogus & all_sections)
