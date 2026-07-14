from app.models.schema import ReferenceType
from app.parsers.reference_extractor import extract_references


def test_single_section_reference():
    refs, general_nw = extract_references("This is subject to Section 4.2 hereof.")
    assert len(refs) == 1
    assert refs[0].type == ReferenceType.SECTION
    assert refs[0].target_section == "4.2"
    assert not refs[0].is_notwithstanding
    assert not general_nw


def test_section_reference_alongside_external_doc_mention():
    """'the Agreement' is itself a real (broad) external-doc reference --
    both it and the section reference should be captured, not just one."""
    refs, _ = extract_references("This is subject to Section 4.2 of the Agreement.")
    by_type = {r.type: r for r in refs}
    assert by_type[ReferenceType.SECTION].target_section == "4.2"
    assert by_type[ReferenceType.EXTERNAL_DOC].target_label == "the Agreement"


def test_multi_number_section_reference():
    refs, _ = extract_references("See Sections 4.2 and 4.3 for details.")
    targets = sorted(r.target_section for r in refs)
    assert targets == ["4.2", "4.3"]


def test_deeply_nested_section_number():
    refs, _ = extract_references("As calculated under Section 4.2.1.")
    assert refs[0].target_section == "4.2.1"


def test_notwithstanding_with_explicit_target():
    text = "Notwithstanding Section 2.2, either party may terminate for convenience."
    refs, general_nw = extract_references(text)
    assert len(refs) == 1
    assert refs[0].target_section == "2.2"
    assert refs[0].is_notwithstanding is True
    assert general_nw is False


def test_notwithstanding_without_target_is_general_override():
    text = "Notwithstanding anything to the contrary contained herein, fees are non-refundable."
    refs, general_nw = extract_references(text)
    assert refs == []
    assert general_nw is True


def test_section_reference_outside_notwithstanding_span_not_flagged():
    text = "Notwithstanding Section 2.2, this rule applies. Separately, Section 5.1 governs invoicing."
    refs, _ = extract_references(text)
    by_target = {r.target_section: r for r in refs}
    assert by_target["2.2"].is_notwithstanding is True
    assert by_target["5.1"].is_notwithstanding is False


def test_exhibit_reference_normalized():
    refs, _ = extract_references("as further detailed in Exhibit C attached hereto")
    assert len(refs) == 1
    assert refs[0].type == ReferenceType.EXHIBIT
    assert refs[0].target_label == "Exhibit C"


def test_schedule_reference_with_number():
    refs, _ = extract_references("per the fee table in Schedule 2")
    assert refs[0].type == ReferenceType.SCHEDULE
    assert refs[0].target_label == "Schedule 2"


def test_lowercase_generic_word_is_not_a_schedule_reference():
    """'schedule' used as an ordinary English word must not be treated as a
    reference to a defined 'Schedule X' exhibit -- this was a real false
    positive found while building the sample contracts."""
    text = "Any change to the scope, fees, or schedule described in this Statement of Work requires a change order."
    refs, _ = extract_references(text)
    assert all(r.type != ReferenceType.SCHEDULE for r in refs)


def test_appendix_and_annexure_variants():
    refs, _ = extract_references("See Appendix 1 and Annexure A for supporting data.")
    types = {r.type for r in refs}
    assert ReferenceType.APPENDIX in types
    assert ReferenceType.ANNEXURE in types


def test_external_doc_reference():
    refs, _ = extract_references("This SOW is issued under the Master Service Agreement.")
    assert any(r.type == ReferenceType.EXTERNAL_DOC and r.target_label == "Master Service Agreement" for r in refs)


def test_no_false_positive_on_plain_text():
    refs, general_nw = extract_references("Provider shall perform the Services in a professional manner.")
    assert refs == []
    assert general_nw is False
