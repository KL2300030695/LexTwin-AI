"""Tests the multi-source playbook loader (app/playbook/__init__.py) against
whichever of the four generated playbook JSON files are actually present:
  - cuad_playbook.json        (scripts/build_cuad_playbook.py)
  - ledgar_playbook.json      (scripts/build_ledgar_playbook.py)
  - unfair_tos_playbook.json  (scripts/build_unfair_tos_playbook.py)
  - contractnli_playbook.json (scripts/build_contractnli_playbook.py)

Each is cheap to load (committed JSON, no raw dataset required at test time)
so these are not marked slow and always run in the default suite.
"""
from pathlib import Path

import pytest

from app.playbook import get_category, list_all_categories, list_categories

PLAYBOOK_DIR = Path(__file__).resolve().parent.parent / "app" / "playbook"


def _requires(filename: str):
    return pytest.mark.skipif(
        not (PLAYBOOK_DIR / filename).exists(),
        reason=f"{filename} not generated -- run the matching scripts/build_*_playbook.py",
    )


requires_cuad = _requires("cuad_playbook.json")
requires_ledgar = _requires("ledgar_playbook.json")
requires_unfair_tos = _requires("unfair_tos_playbook.json")
requires_contractnli = _requires("contractnli_playbook.json")


@requires_cuad
def test_cuad_categories_present_with_source_tag():
    categories = list_categories()
    assert {"source": "CUAD v1", "category": "Governing Law"} in categories
    assert {"source": "CUAD v1", "category": "Cap On Liability"} in categories


@requires_cuad
def test_cuad_category_has_verbatim_examples():
    governing_law = get_category("CUAD v1", "Governing Law")
    assert governing_law is not None
    assert governing_law["contracts_observed_in"] > 0
    assert len(governing_law["example_clauses"]) > 0
    assert isinstance(governing_law["example_clauses"][0], str)


@requires_cuad
def test_cuad_excludes_answer_only_metadata_columns():
    """Sanity check that we pulled verbatim clause text, not the simplified
    Yes/No '-Answer' values -- a real bug found while building this."""
    cuad_categories = [c["category"] for c in list_categories() if c["source"] == "CUAD v1"]
    assert not any(c.endswith("-Answer") for c in cuad_categories)
    cap_on_liability = get_category("CUAD v1", "Cap On Liability")
    assert cap_on_liability is not None
    for example in cap_on_liability["example_clauses"]:
        assert example not in ("Yes", "No")


@requires_ledgar
def test_ledgar_has_100_categories():
    ledgar_categories = [c for c in list_categories() if c["source"] == "LEDGAR (LexGLUE)"]
    assert len(ledgar_categories) == 100
    names = {c["category"] for c in ledgar_categories}
    assert "Governing Laws" in names
    assert "Indemnifications" in names
    assert "Survival" in names


@requires_ledgar
def test_ledgar_category_has_verbatim_examples():
    indemnifications = get_category("LEDGAR (LexGLUE)", "Indemnifications")
    assert indemnifications is not None
    assert indemnifications["example_count"] > 0
    assert len(indemnifications["example_clauses"]) > 0
    assert isinstance(indemnifications["example_clauses"][0], str)


@requires_unfair_tos
def test_unfair_tos_has_8_categories():
    unfair_categories = [c for c in list_categories() if c["source"] == "Unfair ToS (LexGLUE)"]
    assert len(unfair_categories) == 8
    names = {c["category"] for c in unfair_categories}
    assert "Limitation of liability" in names
    assert "Unilateral termination" in names
    assert "Arbitration" in names


@requires_unfair_tos
def test_unfair_tos_category_has_examples():
    limitation = get_category("Unfair ToS (LexGLUE)", "Limitation of liability")
    assert limitation is not None
    assert limitation["example_count"] > 0
    assert len(limitation["example_clauses"]) > 0


@requires_contractnli
def test_contractnli_has_17_hypotheses():
    nli_categories = [c for c in list_categories() if c["source"] == "ContractNLI"]
    assert len(nli_categories) == 17


@requires_contractnli
def test_contractnli_category_has_hypothesis_text_and_examples():
    limited_use = get_category("ContractNLI", "Limited use")
    assert limited_use is not None
    assert "Confidential Information" in limited_use["hypothesis"]
    assert limited_use["example_count"] > 0
    assert len(limited_use["example_clauses"]) > 0
    assert isinstance(limited_use["example_clauses"][0], str)


@requires_cuad
@requires_ledgar
def test_category_lookup_is_scoped_by_source_not_name_alone():
    """CUAD's 'Governing Law' and LEDGAR's 'Governing Laws' are distinct
    strings from distinct sources -- get_category must not conflate them,
    and an unknown (source, name) pair must return None rather than
    silently matching a same-named category from a different source."""
    cuad_result = get_category("CUAD v1", "Governing Law")
    ledgar_result = get_category("LEDGAR (LexGLUE)", "Governing Laws")
    assert cuad_result is not None
    assert ledgar_result is not None
    assert cuad_result["example_clauses"] != ledgar_result["example_clauses"]
    assert get_category("CUAD v1", "Governing Laws") is None


def test_list_all_categories_tags_every_entry_with_its_source():
    for category in list_all_categories():
        assert "source" in category
        assert "category" in category
        assert "example_clauses" in category
