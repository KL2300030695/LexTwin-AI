from app.contradiction.topic_alignment import align_clauses, classify_topic, find_unmatched_clauses
from app.models.schema import Clause, DocType, ParsedDocument


def _clause(doc_id: str, doc_type: DocType, section_number: str, heading: str, text: str = "some body text") -> Clause:
    return Clause(
        id=f"{doc_id}::{section_number}",
        doc_id=doc_id,
        doc_type=doc_type,
        section_number=section_number,
        parent_section=None,
        level=1,
        heading=heading,
        text=text,
        page_start=1,
        page_end=1,
    )


def _doc(doc_id: str, doc_type: DocType, clauses: list[Clause]) -> ParsedDocument:
    return ParsedDocument(doc_id=doc_id, filename=f"{doc_id}.pdf", doc_type=doc_type, clauses=clauses)


def test_classify_topic_basic_cases():
    assert classify_topic("Invoicing and Payment") == "Payment Terms"
    assert classify_topic("Invoice Terms") == "Payment Terms"
    assert classify_topic("Termination for Convenience") == "Termination"
    assert classify_topic("Liability Cap") == "Liability"
    assert classify_topic("General Indemnification") == "Indemnification"
    assert classify_topic("Governing Law") == "Governing Law"


def test_classify_topic_handles_sla_plural():
    """Regression: '\\bsla\\b' doesn't match 'SLAs' (plural) since the word
    boundary requires a non-word char immediately after -- found while
    verifying alignment against the real sample contracts."""
    assert classify_topic("Project-Specific SLAs") == "Service Levels"
    assert classify_topic("Service Level Credits") == "Service Levels"


def test_classify_topic_no_match_returns_none():
    assert classify_topic("General Provisions") is None
    assert classify_topic(None) is None


def test_classify_topic_does_not_match_generic_fee_mentions():
    """'Fixed Fee' / 'Milestone Payment Schedule' should NOT be classified as
    Payment Terms -- only clauses about invoicing/payment terms specifically
    should align, not every clause that mentions money."""
    assert classify_topic("Fixed Fee") is None
    assert classify_topic("Milestone Payment Schedule") is None
    assert classify_topic("Late Payment Penalty") is None


def test_align_clauses_pairs_matching_topics():
    msa = _doc("msa1", DocType.MSA, [
        _clause("msa1", DocType.MSA, "5.1", "Invoicing and Payment", "Pay within 45 days."),
        _clause("msa1", DocType.MSA, "6.1", "Liability Cap", "Capped at fees paid."),
    ])
    sow = _doc("sow1", DocType.SOW, [
        _clause("sow1", DocType.SOW, "3.3", "Invoice Terms", "Pay within 15 days."),
    ])

    pairs = align_clauses(msa, sow)
    assert len(pairs) == 1
    assert pairs[0].topic == "Payment Terms"
    assert pairs[0].msa_clause.section_number == "5.1"
    assert pairs[0].sow_clause.section_number == "3.3"


def test_align_clauses_topic_only_in_one_doc_not_paired():
    msa = _doc("msa1", DocType.MSA, [
        _clause("msa1", DocType.MSA, "6.1", "Liability Cap", "text"),
    ])
    sow = _doc("sow1", DocType.SOW, [
        _clause("sow1", DocType.SOW, "1.1", "Project Overview", "text"),
    ])
    assert align_clauses(msa, sow) == []


def test_align_clauses_picks_first_non_empty_match_per_topic():
    """If a doc has multiple clauses matching the same topic, only the first
    one with actual body text is used -- a bare section header with no text
    of its own (common for top-level container headings) is skipped."""
    msa = _doc("msa1", DocType.MSA, [
        _clause("msa1", DocType.MSA, "5", "Fees And Payment Terms", text=""),  # header only, no text
        _clause("msa1", DocType.MSA, "5.1", "Invoicing and Payment", "Pay within 45 days."),
        _clause("msa1", DocType.MSA, "5.2", "Late Payment Penalty", "1% per day."),
    ])
    sow = _doc("sow1", DocType.SOW, [
        _clause("sow1", DocType.SOW, "3.3", "Invoice Terms", "Pay within 15 days."),
    ])

    pairs = align_clauses(msa, sow)
    assert len(pairs) == 1
    assert pairs[0].msa_clause.section_number == "5.1"


def test_align_clauses_empty_documents():
    msa = _doc("msa1", DocType.MSA, [])
    sow = _doc("sow1", DocType.SOW, [])
    assert align_clauses(msa, sow) == []


def test_find_unmatched_clauses_reports_clauses_with_no_topic_match():
    """A clause whose heading matches no configured topic never becomes an
    align_clauses() pair -- find_unmatched_clauses() is the coverage report
    that surfaces it, since otherwise it's invisible: no result entry, no
    cannot_evaluate status, nothing."""
    msa = _doc("msa1", DocType.MSA, [
        _clause("msa1", DocType.MSA, "5.1", "Invoicing and Payment", "Pay within 45 days."),
        _clause("msa1", DocType.MSA, "8.1", "Data Security Requirements", "Encrypt data at rest."),
    ])
    sow = _doc("sow1", DocType.SOW, [
        _clause("sow1", DocType.SOW, "3.3", "Invoice Terms", "Pay within 15 days."),
    ])

    unmatched = find_unmatched_clauses(msa, sow)
    assert len(unmatched) == 1
    assert unmatched[0].doc_id == "msa1"
    assert unmatched[0].clause.section_number == "8.1"


def test_find_unmatched_clauses_excludes_matched_clauses():
    msa = _doc("msa1", DocType.MSA, [
        _clause("msa1", DocType.MSA, "5.1", "Invoicing and Payment", "Pay within 45 days."),
    ])
    sow = _doc("sow1", DocType.SOW, [
        _clause("sow1", DocType.SOW, "3.3", "Invoice Terms", "Pay within 15 days."),
    ])
    assert find_unmatched_clauses(msa, sow) == []


def test_find_unmatched_clauses_excludes_empty_text_and_missing_section_number():
    msa = _doc("msa1", DocType.MSA, [
        _clause("msa1", DocType.MSA, "5", "Fees And Payment Terms", text=""),  # header only
        Clause(
            id="msa1::preamble", doc_id="msa1", doc_type=DocType.MSA, section_number=None,
            parent_section=None, level=0, heading="Preamble", text="Some preamble text.",
            page_start=1, page_end=1,
        ),
    ])
    sow = _doc("sow1", DocType.SOW, [])
    assert find_unmatched_clauses(msa, sow) == []
