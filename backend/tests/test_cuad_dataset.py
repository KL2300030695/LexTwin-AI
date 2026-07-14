"""Validates the CUAD v1 dataset (added under data/cuad/CUAD_v1/)
and stress-tests the Phase 2 parser against real, unstructured legal contracts
rather than only our clean synthetic MSA/SOW pair.

These are deliberately looser than test_pdf_parser.py's exact-hierarchy checks:
real CUAD contracts vary hugely in drafting style (decimal outline, inline
"1. Title. Body..." paragraphs, lettered sub-clauses, no numbering at all), so
the bar here is "doesn't crash and extracts something", not "matches an exact
hierarchy". test_pdf_parser.py (our own generated samples) is what enforces
exact hierarchy/reference correctness.

The dataset-driven tests below are marked `slow` (PyMuPDF's find_tables() on a
70+ page real contract dominates the runtime) and are deselected by default --
see pytest.ini's `addopts = -m "not slow"`. Run them explicitly with:
    pytest -m slow tests/test_cuad_dataset.py

See test_playbook.py for tests of the playbook built from this dataset (and
the other three datasets under data/).
"""
import csv
import random
from pathlib import Path

import pytest

from app.models.schema import DocType
from app.parsers import parse_document

DATASET_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "cuad"
    / "CUAD_v1"
)
CSV_PATH = DATASET_DIR / "master_clauses.csv"
PDF_DIR = DATASET_DIR / "full_contract_pdf"

requires_dataset = pytest.mark.skipif(
    not CSV_PATH.exists(),
    reason="CUAD dataset not present -- see data/cuad/CUAD_v1/",
)
slow_and_requires_dataset = [requires_dataset, pytest.mark.slow]


@pytest.fixture(scope="module")
def cuad_rows():
    with CSV_PATH.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def pdf_filename_index() -> dict[str, Path]:
    """filename -> path, built with a single tree walk (510 files across
    nested Part_I/Part_II/<category> subfolders -- much cheaper than one
    rglob() per row)."""
    return {p.name: p for p in PDF_DIR.rglob("*.pdf")}


@requires_dataset
def test_master_clauses_csv_has_expected_shape(cuad_rows):
    assert len(cuad_rows) == 510
    assert "Filename" in cuad_rows[0]
    assert "Governing Law" in cuad_rows[0]
    assert "Governing Law-Answer" in cuad_rows[0]


def _resolve_cuad_pdf(csv_filename: str, index: dict[str, Path]) -> Path | None:
    """Resolves a master_clauses.csv 'Filename' value to an actual PDF path.

    ~2% of CUAD v1's rows don't match the on-disk filename exactly -- a known
    upstream packaging quirk where '&' and stray quote characters in the
    original filename were sanitized to '_' when the release zip was built
    (e.g. CSV says 'MOELIS&CO_...STRATEGIC ALLIANCE AGREEMENT.PDF', the file
    on disk is 'MOELIS_CO_...STRATEGIC ALLIANCE AGREEMENT.PDF'). Most rows
    resolve once normalized this way; see _KNOWN_UNRESOLVABLE_FILENAMES below
    for the handful that don't resolve under any variant.
    """
    if csv_filename in index:
        return index[csv_filename]
    normalized = csv_filename.rstrip("'").replace("&", "_").replace("'", "_")
    if normalized in index:
        return index[normalized]
    # A handful of files were archived under a compound name covering two
    # clause labels (e.g. "...Development Agreement.PDF" on disk is
    # "..._Development Agreement_Option Agreement.pdf"); match by prefix.
    stem = Path(normalized).stem
    for name, path in index.items():
        if name.startswith(stem):
            return path
    return None


# 13 of 510 master_clauses.csv rows reference PDFs that are genuinely absent
# from the official CUAD v1 full_contract_pdf/ release (verified: not present
# under any filename variant, not a truncated/corrupted download -- confirmed
# by searching the whole archive for distinctive substrings from each name).
# A real upstream data-quality gap, not something normalization can fix.
_KNOWN_UNRESOLVABLE_FILENAMES = {
    "AudibleInc_20001113_10-Q_EX-10.32_2599586_EX-10.32_Co-Branding Agreement_ Marketing Agreement_ Investment Distribution Agreement.pdf",
    "PlayboyEnterprisesInc_20090220_10-QA_EX-10.2_4091580_EX-10.2_Content License Agreement_ Marketing Agreement_ Sales-Purchase Agreement1.pdf",
    "PlayboyEnterprisesInc_20090220_10-QA_EX-10.2_4091580_EX-10.2_Content License Agreement_ Marketing Agreement_ Sales-Purchase Agreement2.pdf",
    "EMERALDHEALTHTHERAPEUTICSINC_06_10_2020-EX-4.5-CONSULTING AGREEMENT - DR. GAETANO MORELLO N.D. INC..PDF",
    "WELLSFARGOMORTGAGEBACKEDSECURITIES2006-6TRUST_05_11_2006-EX-10.3-Yield Maintenance Agreement.PDF",
    "IDREAMSKYTECHNOLOGYLTD_07_03_2014-EX-10.39-Cooperation Agreement on Mobile Game Business.PDF",
    "BABCOCK_WILCOXENTERPRISES,INC_08_04_2015-EX-10.17-INTELLECTUAL PROPERTY AGREEMENT between THE BABCOCK _ WILCOX COMPANY and BABCOCK _ WILCOX ENTERPRISES, INC..PDF",
    "FEDERATEDGOVERNMENTINCOMESECURITIESINC_04_28_2020-EX-99.SERV AGREE-SERVICES AGREEMENT_SECONDAMENDMENT.pdf",
    "FEDERATEDGOVERNMENTINCOMESECURITIESINC_04_28_2020-EX-99.SERV AGREE-SERVICES AGREEMENT_AMENDMENT.pdf",
    "SPIENERGYCO,LTD_07_10_2014-EX-10-Cooperation Agreement of 50MWp Photovoltaic Grid-connected Power Generation Project in Yangqiao of~1.PDF",
    "OTISWORLDWIDECORP_04_03_2020-EX-10.4-INTELLECTUAL PROPERTY AGREEMENT by and among UNITED TECHNOLOGIES CORPORATION, OTIS WORLDWIDE CORPORATION and CARRIER ~1.PDF",
    "NETGEAR,INC_04_21_2003-EX-10.16-AMENDMENT TO THE DISTRIBUTOR AGREEMENT BETWEEN INGRAM MICRO AND NETGEAR-.pdf",
    "WOMENSGOLFUNLIMITEDINC_03_29_2000-EX-10.13-ENDORSEMENT AGREEMENT - Intellectual Property Rights                 Confidentiality and Non-Use Obligations Agreement.pdf",
}


@requires_dataset
def test_every_row_has_a_resolvable_pdf(cuad_rows, pdf_filename_index):
    missing = {row["Filename"] for row in cuad_rows if _resolve_cuad_pdf(row["Filename"], pdf_filename_index) is None}
    unexpected = missing - _KNOWN_UNRESOLVABLE_FILENAMES
    assert unexpected == set(), (
        f"{len(unexpected)} newly-unresolvable PDF(s) not covered by the known-gap list: {sorted(unexpected)[:5]}"
    )


@pytest.fixture(scope="module")
def parsed_real_contract_sample(pdf_filename_index):
    """Parses a fixed, varied sample of 15 real contracts exactly once, so
    multiple assertions can share the result instead of each re-parsing."""
    rng = random.Random(42)
    sample_paths = rng.sample(sorted(pdf_filename_index.values()), min(15, len(pdf_filename_index)))
    results = []
    for pdf_path in sample_paths:
        try:
            parsed = parse_document(str(pdf_path), "cuad-test", pdf_path.name, DocType.OTHER)
            results.append((pdf_path, parsed, None))
        except Exception as e:  # noqa: BLE001 -- collecting failures across the whole sample on purpose
            results.append((pdf_path, None, e))
    return results


@pytest.mark.slow
@requires_dataset
def test_parser_does_not_crash_on_real_contracts(parsed_real_contract_sample):
    failures = [(path.name, repr(err)) for path, _, err in parsed_real_contract_sample if err is not None]
    assert failures == [], f"Parser raised on {len(failures)}/{len(parsed_real_contract_sample)} real contracts"


@pytest.mark.slow
@requires_dataset
def test_parser_extracts_some_structure_from_most_real_contracts(parsed_real_contract_sample):
    """Not every real contract uses decimal section numbering (some are short,
    informally drafted agreements) -- but the large majority should still
    yield more than just a single 'Preamble' blob."""
    parsed_docs = [parsed for _, parsed, err in parsed_real_contract_sample if err is None]
    assert len(parsed_docs) == len(parsed_real_contract_sample), "some contracts failed to parse at all"
    for parsed in parsed_docs:
        assert len(parsed.clauses) >= 1
        assert any(c.text.strip() for c in parsed.clauses)
    with_structure = sum(1 for parsed in parsed_docs if len(parsed.clauses) > 1)
    assert with_structure / len(parsed_docs) >= 0.6


@pytest.mark.slow
@requires_dataset
def test_well_structured_real_msa_style_contract_parses_cleanly(pdf_filename_index):
    """A real, 71-page, decimal-numbered maintenance agreement should parse
    with full section/parent hierarchy, same as our synthetic MSA does."""
    match = next((p for name, p in pdf_filename_index.items() if name.startswith("AtnInternationalInc") and "Maintenance" in name), None)
    if match is None:
        pytest.skip("specific fixture contract not present in this dataset copy")
    parsed = parse_document(str(match), "cuad-test", match.name, DocType.OTHER)
    assert parsed.page_count > 50
    numbered = [c for c in parsed.clauses if c.section_number and "." in (c.section_number or "")]
    assert len(numbered) > 30
    assert all(c.parent_section for c in numbered)


@requires_dataset
def test_inline_heading_style_real_contract_is_recognized(pdf_filename_index):
    """Regression guard for the 'N. Title. Body text...' inline heading
    fallback added after finding this in a real CUAD contract. Cheap (3-page
    PDF) -- not marked slow."""
    match = next((p for name, p in pdf_filename_index.items() if name.startswith("Freecook") and "Hosting" in name), None)
    if match is None:
        pytest.skip("specific fixture contract not present in this dataset copy")
    parsed = parse_document(str(match), "cuad-test", match.name, DocType.OTHER)
    sections = {c.section_number: c.heading for c in parsed.clauses}
    assert sections.get("1") == "Website Design and Development"
    assert sections.get("2") == "Payment Terms"
