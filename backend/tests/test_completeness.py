"""Hand-built Clause/ParsedDocument fixtures for precise control over the
missing-reference / refusal check. See test_completeness_integration.py for
checks against the real sample contracts."""
from app.completeness import check_completeness
from app.models.schema import Clause, DocType, ParsedDocument, Reference, ReferenceType


def _exhibit_ref(label: str, kind: ReferenceType = ReferenceType.EXHIBIT, char_start: int = 0) -> Reference:
    raw_text = label
    return Reference(
        raw_text=raw_text,
        type=kind,
        target_label=label,
        char_start=char_start,
        char_end=char_start + len(raw_text),
        context=raw_text,
    )


def _external_doc_ref(label: str, char_start: int = 0) -> Reference:
    return Reference(
        raw_text=label,
        type=ReferenceType.EXTERNAL_DOC,
        target_label=label,
        char_start=char_start,
        char_end=char_start + len(label),
        context=label,
    )


def _section_ref(target_section: str, char_start: int = 0) -> Reference:
    raw_text = f"Section {target_section}"
    return Reference(
        raw_text=raw_text,
        type=ReferenceType.SECTION,
        target_section=target_section,
        char_start=char_start,
        char_end=char_start + len(raw_text),
        context=raw_text,
    )


def _clause(doc_id: str, doc_type: DocType, section_number: str, text: str, references: list[Reference] | None = None) -> Clause:
    return Clause(
        id=f"{doc_id}::{section_number}",
        doc_id=doc_id,
        doc_type=doc_type,
        section_number=section_number,
        parent_section=None,
        level=1,
        heading=f"Clause {section_number}",
        text=text,
        page_start=1,
        page_end=1,
        references=references or [],
    )


def _doc(doc_id: str, doc_type: DocType, clauses: list[Clause], available_exhibit_labels: list[str] | None = None) -> ParsedDocument:
    return ParsedDocument(
        doc_id=doc_id,
        filename=f"{doc_id}.pdf",
        doc_type=doc_type,
        clauses=clauses,
        available_exhibit_labels=available_exhibit_labels or [],
    )


def test_clause_referencing_uploaded_exhibit_can_evaluate():
    clause = _clause("d1", DocType.MSA, "4.3", "See Exhibit A.", [_exhibit_ref("Exhibit A")])
    doc = _doc("d1", DocType.MSA, [clause], available_exhibit_labels=["Exhibit A"])

    result = check_completeness([doc])
    status = result.clause_statuses[0]
    assert status.can_evaluate is True
    assert status.missing_references == []
    assert status.reason is None


def test_clause_referencing_missing_exhibit_cannot_evaluate():
    clause = _clause("d1", DocType.MSA, "4.3", "See Exhibit C.", [_exhibit_ref("Exhibit C")])
    doc = _doc("d1", DocType.MSA, [clause], available_exhibit_labels=["Exhibit A", "Exhibit B"])

    result = check_completeness([doc])
    status = result.clause_statuses[0]
    assert status.can_evaluate is False
    assert status.reason is not None
    assert "Exhibit C" in status.reason
    assert len(status.missing_references) == 1
    assert status.missing_references[0].label == "Exhibit C"
    assert status.missing_references[0].type == "exhibit"
    assert result.blocked_clause_count == 1
    assert result.total_clause_count == 1


def test_exhibit_available_via_a_different_document_in_the_set():
    """The SOW references Exhibit A, which actually lives in the MSA -- when
    both are analyzed together it must resolve as available."""
    sow_clause = _clause("sow1", DocType.SOW, "5.2", "See Exhibit A of the MSA.", [_exhibit_ref("Exhibit A")])
    sow_doc = _doc("sow1", DocType.SOW, [sow_clause], available_exhibit_labels=[])
    msa_doc = _doc("msa1", DocType.MSA, [_clause("msa1", DocType.MSA, "Exhibit A", "content")], available_exhibit_labels=["Exhibit A"])

    result = check_completeness([sow_doc, msa_doc])
    status = next(s for s in result.clause_statuses if s.clause_id == "sow1::5.2")
    assert status.can_evaluate is True


def test_exhibit_missing_when_other_document_not_in_analyzed_set():
    """Same clause, but the MSA isn't included in this analysis -- must be
    flagged, not assumed available."""
    sow_clause = _clause("sow1", DocType.SOW, "5.2", "See Exhibit A of the MSA.", [_exhibit_ref("Exhibit A")])
    sow_doc = _doc("sow1", DocType.SOW, [sow_clause], available_exhibit_labels=[])

    result = check_completeness([sow_doc])
    status = result.clause_statuses[0]
    assert status.can_evaluate is False
    assert status.missing_references[0].label == "Exhibit A"


def test_named_external_document_missing_from_set():
    clause = _clause("sow1", DocType.SOW, "1", "Issued under the Master Service Agreement.", [_external_doc_ref("Master Service Agreement")])
    doc = _doc("sow1", DocType.SOW, [clause])

    result = check_completeness([doc])
    status = result.clause_statuses[0]
    assert status.can_evaluate is False
    assert status.missing_references[0].type == "external_document"
    assert status.missing_references[0].label == "Master Service Agreement"


def test_named_external_document_present_in_set():
    clause = _clause("sow1", DocType.SOW, "1", "Issued under the Master Service Agreement.", [_external_doc_ref("Master Service Agreement")])
    sow_doc = _doc("sow1", DocType.SOW, [clause])
    msa_doc = _doc("msa1", DocType.MSA, [_clause("msa1", DocType.MSA, "1", "x")])

    result = check_completeness([sow_doc, msa_doc])
    status = next(s for s in result.clause_statuses if s.clause_id == "sow1::1")
    assert status.can_evaluate is True


def test_this_agreement_phrase_never_flagged_as_missing():
    """'this Agreement' / 'the Agreement' means the current document, not a
    pointer to some other missing document -- must never be flagged."""
    clause = _clause("d1", DocType.MSA, "1", "governed by the laws applicable to this Agreement", [_external_doc_ref("the Agreement")])
    doc = _doc("d1", DocType.MSA, [clause])

    result = check_completeness([doc])
    assert result.clause_statuses[0].can_evaluate is True


def test_cross_document_section_reference_to_missing_document():
    ref_text = "Section 4.2 of the Master Service Agreement"
    refs = [
        _section_ref("4.2", char_start=0),
        _external_doc_ref("Master Service Agreement", char_start=len("Section 4.2 of the ")),
    ]
    clause = _clause("sow1", DocType.SOW, "4.1", ref_text, refs)
    doc = _doc("sow1", DocType.SOW, [clause])

    result = check_completeness([doc])
    status = result.clause_statuses[0]
    assert status.can_evaluate is False
    assert "4.2" in status.missing_references[0].label
    assert "Master Service Agreement" in status.missing_references[0].label


def test_plain_section_reference_within_same_doc_is_not_a_completeness_issue():
    clause = _clause("d1", DocType.MSA, "5.3", "See Section 5.1.", [_section_ref("5.1")])
    doc = _doc("d1", DocType.MSA, [clause])
    result = check_completeness([doc])
    assert result.clause_statuses[0].can_evaluate is True


def test_duplicate_missing_reference_in_same_clause_deduplicated():
    clause = _clause(
        "d1", DocType.MSA, "1", "See Exhibit C here and Exhibit C again.",
        [_exhibit_ref("Exhibit C", char_start=4), _exhibit_ref("Exhibit C", char_start=25)],
    )
    doc = _doc("d1", DocType.MSA, [clause])
    result = check_completeness([doc])
    assert len(result.clause_statuses[0].missing_references) == 1


def test_clauses_without_section_number_excluded_from_counts():
    """The preamble clause (section_number=None) shouldn't count toward
    total/blocked -- it's not a numbered, individually-evaluable clause."""
    preamble = Clause(
        id="d1::preamble", doc_id="d1", doc_type=DocType.MSA, section_number=None,
        parent_section=None, level=0, heading="Preamble", text="intro text",
        page_start=1, page_end=1,
    )
    doc = _doc("d1", DocType.MSA, [preamble])
    result = check_completeness([doc])
    assert result.total_clause_count == 0
    assert result.clause_statuses == []


def test_available_doc_types_and_exhibits_reflect_analyzed_set():
    msa_doc = _doc("msa1", DocType.MSA, [_clause("msa1", DocType.MSA, "1", "x")], available_exhibit_labels=["Exhibit A"])
    sow_doc = _doc("sow1", DocType.SOW, [_clause("sow1", DocType.SOW, "1", "y")], available_exhibit_labels=["Exhibit D"])

    result = check_completeness([msa_doc, sow_doc])
    assert set(result.available_doc_types) == {DocType.MSA, DocType.SOW}
    assert set(result.available_exhibit_labels) == {"Exhibit A", "Exhibit D"}
