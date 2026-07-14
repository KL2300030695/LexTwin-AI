"""Runs the dependency graph builder against the real synthetic MSA + SOW
samples (same fixtures as test_pdf_parser.py) to confirm the three seeded
issues surface correctly end-to-end: the MSA's circular reference, the
Notwithstanding overrides in both documents, and the SOW-to-MSA cross-document
reference resolution."""
from pathlib import Path

import pytest

from app.graph.dependency_graph import build_dependency_graph
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


def test_msa_alone_surfaces_seeded_circular_reference(msa):
    result = build_dependency_graph([msa])
    cycles = result.analysis.circular_references
    assert len(cycles) == 1
    assert set(cycles[0].clause_ids) == {"msa-test::6.3", "msa-test::9.1"}
    assert cycles[0].severity == "circular_reference"  # no Notwithstanding involved in this one


def test_msa_notwithstanding_override_resolved(msa):
    result = build_dependency_graph([msa])
    overrides = {(o.overriding_clause_id, o.overridden_clause_id) for o in result.analysis.overrides}
    assert ("msa-test::2.3", "msa-test::2.2") in overrides


def test_sow_notwithstanding_override_resolved(sow):
    result = build_dependency_graph([sow])
    overrides = {(o.overriding_clause_id, o.overridden_clause_id) for o in result.analysis.overrides}
    assert ("sow-test::7.2", "sow-test::6.1") in overrides


def test_sow_alone_cannot_resolve_msa_cross_reference(sow):
    """SOW 4.1 references 'Section 4.2 of the Master Service Agreement' --
    with only the SOW in scope, that must come back unresolved, not silently
    misattributed to some unrelated section."""
    result = build_dependency_graph([sow])
    unresolved_targets = {u.target_section for u in result.analysis.unresolved_references}
    assert "4.2" in unresolved_targets
    assert not any(e.source == "sow-test::4.1" for e in result.analysis.edges)


def test_msa_and_sow_together_resolve_cross_document_reference(msa, sow):
    result = build_dependency_graph([msa, sow])
    edge = next((e for e in result.analysis.edges if e.source == "sow-test::4.1"), None)
    assert edge is not None
    assert edge.target == "msa-test::4.2"


def test_no_spurious_cycles_introduced_by_combining_documents(msa, sow):
    """Combining MSA+SOW must not create new cycles beyond the one already
    known to exist purely within the MSA."""
    result = build_dependency_graph([msa, sow])
    assert len(result.analysis.circular_references) == 1
    assert set(result.analysis.circular_references[0].clause_ids) == {"msa-test::6.3", "msa-test::9.1"}


def test_no_general_overrides_in_current_samples(msa, sow):
    """Neither sample currently uses a targetless 'Notwithstanding anything
    to the contrary' -- both Notwithstanding clauses name a specific section.
    This pins down current behavior; general-override handling itself is
    covered by hand-built fixtures in test_dependency_graph.py."""
    result = build_dependency_graph([msa, sow])
    assert result.analysis.general_overrides == []
