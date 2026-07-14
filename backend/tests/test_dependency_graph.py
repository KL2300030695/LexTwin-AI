"""Hand-built Clause/ParsedDocument fixtures give precise control over edge
cases (cross-document redirects, unresolved references, self-references,
general overrides) without depending on real PDF parsing. See
test_dependency_graph_integration.py for the real-sample-driven checks."""
from app.graph.dependency_graph import build_dependency_graph
from app.models.schema import Clause, DocType, ParsedDocument, Reference, ReferenceType


def _section_ref(target_section: str, raw_text: str | None = None, is_notwithstanding: bool = False, char_start: int = 0) -> Reference:
    raw_text = raw_text or f"Section {target_section}"
    return Reference(
        raw_text=raw_text,
        type=ReferenceType.SECTION,
        target_section=target_section,
        is_notwithstanding=is_notwithstanding,
        char_start=char_start,
        char_end=char_start + len(raw_text),
        context=raw_text,
    )


def _external_doc_ref(label: str, char_start: int) -> Reference:
    return Reference(
        raw_text=label,
        type=ReferenceType.EXTERNAL_DOC,
        target_label=label,
        char_start=char_start,
        char_end=char_start + len(label),
        context=label,
    )


def _clause(doc_id: str, doc_type: DocType, section_number: str, text: str, references: list[Reference] | None = None, has_general_override: bool = False) -> Clause:
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
        has_general_override=has_general_override,
    )


def _doc(doc_id: str, doc_type: DocType, clauses: list[Clause]) -> ParsedDocument:
    return ParsedDocument(doc_id=doc_id, filename=f"{doc_id}.pdf", doc_type=doc_type, clauses=clauses)


def test_simple_two_clause_cycle_detected():
    a = _clause("d1", DocType.MSA, "6.3", "See Section 9.1.", [_section_ref("9.1")])
    b = _clause("d1", DocType.MSA, "9.1", "See Section 6.3.", [_section_ref("6.3")])
    result = build_dependency_graph([_doc("d1", DocType.MSA, [a, b])])

    assert len(result.analysis.circular_references) == 1
    cycle = result.analysis.circular_references[0]
    assert set(cycle.clause_ids) == {"d1::6.3", "d1::9.1"}
    assert cycle.severity == "circular_reference"


def test_cycle_of_pure_notwithstanding_edges_is_override_conflict():
    a = _clause("d1", DocType.MSA, "1", "x", [_section_ref("2", is_notwithstanding=True)])
    b = _clause("d1", DocType.MSA, "2", "y", [_section_ref("1", is_notwithstanding=True)])
    result = build_dependency_graph([_doc("d1", DocType.MSA, [a, b])])

    cycle = result.analysis.circular_references[0]
    assert cycle.severity == "override_conflict"


def test_no_cycle_for_one_directional_chain():
    a = _clause("d1", DocType.MSA, "1", "x", [_section_ref("2")])
    b = _clause("d1", DocType.MSA, "2", "y", [])
    result = build_dependency_graph([_doc("d1", DocType.MSA, [a, b])])
    assert result.analysis.circular_references == []


def test_self_reference_does_not_create_edge_or_cycle():
    a = _clause("d1", DocType.MSA, "9.1", "obligations under this Section 9.1", [_section_ref("9.1")])
    result = build_dependency_graph([_doc("d1", DocType.MSA, [a])])
    assert result.analysis.edges == []
    assert result.analysis.circular_references == []


def test_notwithstanding_override_direction():
    """2.3 says 'Notwithstanding Section 2.2' -- 2.3 is the one that takes
    precedence (overrides), 2.2 is the one being superseded."""
    overriding = _clause("d1", DocType.MSA, "2.3", "Notwithstanding Section 2.2...", [_section_ref("2.2", is_notwithstanding=True)])
    overridden = _clause("d1", DocType.MSA, "2.2", "text", [])
    result = build_dependency_graph([_doc("d1", DocType.MSA, [overriding, overridden])])

    assert len(result.analysis.overrides) == 1
    override = result.analysis.overrides[0]
    assert override.overriding_clause_id == "d1::2.3"
    assert override.overridden_clause_id == "d1::2.2"


def test_general_override_with_no_target_reported_separately():
    a = _clause("d1", DocType.MSA, "1", "Notwithstanding anything to the contrary herein, fees are non-refundable.", has_general_override=True)
    result = build_dependency_graph([_doc("d1", DocType.MSA, [a])])

    assert len(result.analysis.general_overrides) == 1
    assert result.analysis.general_overrides[0].clause_id == "d1::1"
    assert "Notwithstanding" in result.analysis.general_overrides[0].snippet
    assert result.analysis.overrides == []


def test_unresolved_reference_to_nonexistent_section():
    a = _clause("d1", DocType.MSA, "1", "See Section 99.9.", [_section_ref("99.9")])
    result = build_dependency_graph([_doc("d1", DocType.MSA, [a])])

    assert len(result.analysis.unresolved_references) == 1
    assert result.analysis.unresolved_references[0].target_section == "99.9"
    assert result.analysis.edges == []


def test_cross_document_reference_resolved_when_both_docs_present():
    ref_text = "Section 4.2 of the Master Service Agreement"
    refs = [
        _section_ref("4.2", raw_text="Section 4.2", char_start=0),
        _external_doc_ref("Master Service Agreement", char_start=len("Section 4.2 of the ")),
    ]
    sow_clause = _clause("sow1", DocType.SOW, "4.1", ref_text, refs)
    msa_clause = _clause("msa1", DocType.MSA, "4.2", "SLA terms", [])

    result = build_dependency_graph(
        [_doc("sow1", DocType.SOW, [sow_clause]), _doc("msa1", DocType.MSA, [msa_clause])]
    )

    assert result.analysis.unresolved_references == []
    assert len(result.analysis.edges) == 1
    edge = result.analysis.edges[0]
    assert edge.source == "sow1::4.1"
    assert edge.target == "msa1::4.2"


def test_cross_document_reference_unresolved_when_other_doc_absent():
    """Same SOW clause as above, but analyzed alone -- the MSA it points to
    isn't in the set, so this must NOT silently fall back to a same-document
    match (there is no 4.2 in the SOW itself here)."""
    ref_text = "Section 4.2 of the Master Service Agreement"
    refs = [
        _section_ref("4.2", raw_text="Section 4.2", char_start=0),
        _external_doc_ref("Master Service Agreement", char_start=len("Section 4.2 of the ")),
    ]
    sow_clause = _clause("sow1", DocType.SOW, "4.1", ref_text, refs)

    result = build_dependency_graph([_doc("sow1", DocType.SOW, [sow_clause])])

    assert result.analysis.edges == []
    assert len(result.analysis.unresolved_references) == 1
    assert result.analysis.unresolved_references[0].target_section == "4.2"


def test_cross_document_redirect_does_not_match_wrong_document_same_section_number():
    """If the SOW itself also happens to have its own Section 4.2, a
    reference explicitly qualified 'of the Master Service Agreement' must
    still resolve to the MSA's 4.2, not the SOW's own 4.2."""
    ref_text = "Section 4.2 of the Master Service Agreement"
    refs = [
        _section_ref("4.2", raw_text="Section 4.2", char_start=0),
        _external_doc_ref("Master Service Agreement", char_start=len("Section 4.2 of the ")),
    ]
    sow_referencing_clause = _clause("sow1", DocType.SOW, "4.1", ref_text, refs)
    sow_own_4_2 = _clause("sow1", DocType.SOW, "4.2", "SOW's own unrelated section", [])
    msa_clause = _clause("msa1", DocType.MSA, "4.2", "SLA terms", [])

    result = build_dependency_graph(
        [_doc("sow1", DocType.SOW, [sow_referencing_clause, sow_own_4_2]), _doc("msa1", DocType.MSA, [msa_clause])]
    )

    assert len(result.analysis.edges) == 1
    assert result.analysis.edges[0].target == "msa1::4.2"


def test_plain_section_reference_without_qualifier_resolves_same_document():
    a = _clause("d1", DocType.MSA, "5.3", "See Section 5.1.", [_section_ref("5.1")])
    b = _clause("d1", DocType.MSA, "5.1", "text", [])
    result = build_dependency_graph([_doc("d1", DocType.MSA, [a, b])])

    assert len(result.analysis.edges) == 1
    assert result.analysis.edges[0].target == "d1::5.1"
