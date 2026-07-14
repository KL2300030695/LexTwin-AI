from app.models.schema import DocType, TableModel
from app.parsers.structure import Line, TableAnchor, build_document, parent_of, parse_heading


def test_parse_heading_numeric():
    assert parse_heading("4.2.1 Penalty Calculation Method") == ("4.2.1", "Penalty Calculation Method", 3)


def test_parse_heading_top_level():
    assert parse_heading("4 PAYMENT TERMS") == ("4", "PAYMENT TERMS", 1)


def test_parse_heading_rejects_mid_sentence_reference():
    assert parse_heading("as described in Section 4.2 above, the fee applies") is None


def test_parse_heading_rejects_bare_number_line():
    assert parse_heading("2026-02-15") is None


def test_parse_heading_accepts_quoted_title():
    assert parse_heading('1.1 "Confidential Information" Definition') is not None


def test_parse_heading_exhibit():
    parsed = parse_heading("EXHIBIT C SERVICE LEVEL AGREEMENT")
    assert parsed is not None
    num, title, level = parsed
    assert num == "Exhibit C"
    assert level == 1


def test_parent_of():
    assert parent_of("4.2.1") == "4.2"
    assert parent_of("4.2") == "4"
    assert parent_of("4") is None
    assert parent_of("Exhibit C") is None


def _lines(*texts_and_pages: tuple[str, int]) -> list[Line]:
    return [Line(text=t, page=p) for t, p in texts_and_pages]


def test_build_document_hierarchy_and_parents():
    lines = _lines(
        ("4 PAYMENT TERMS", 1),
        ("Intro text for payment terms.", 1),
        ("4.1 Invoicing", 1),
        ("Provider shall invoice monthly.", 1),
        ("4.2 Late Payment", 1),
        ("Penalties accrue per Section 4.2.1 below.", 1),
        ("4.2.1 Penalty Calculation", 1),
        ("Calculated at 1% per day.", 1),
        ("5 LIABILITY", 2),
        ("Liability is capped as described herein.", 2),
    )
    doc = build_document("doc1", "test.pdf", DocType.MSA, lines, [], page_count=2)
    by_num = {c.section_number: c for c in doc.clauses}

    assert by_num["4"].parent_section is None
    assert by_num["4"].level == 1
    assert by_num["4.1"].parent_section == "4"
    assert by_num["4.2"].parent_section == "4"
    assert by_num["4.2.1"].parent_section == "4.2"
    assert by_num["4.2.1"].level == 3
    assert by_num["5"].page_start == 2

    assert "Provider shall invoice monthly." in by_num["4.1"].text
    assert "Calculated at 1% per day." in by_num["4.2.1"].text
    # body text of 4.2 should not leak into 4.2.1 or vice versa
    assert "Calculated at 1% per day." not in by_num["4.2"].text


def test_build_document_sibling_after_deeper_child_closes_correctly():
    """4.2.1 is open, then 4.3 arrives -- 4.3 must close 4.2.1 AND 4.2, not just 4.2.1."""
    lines = _lines(
        ("4 PAYMENT TERMS", 1),
        ("4.2 Late Payment", 1),
        ("4.2.1 Penalty Calculation", 1),
        ("penalty text", 1),
        ("4.3 Taxes", 1),
        ("tax text", 1),
    )
    doc = build_document("doc1", "test.pdf", DocType.MSA, lines, [], page_count=1)
    by_num = {c.section_number: c for c in doc.clauses}
    assert by_num["4.3"].parent_section == "4"
    assert "tax text" in by_num["4.3"].text
    assert "tax text" not in by_num["4.2.1"].text


def test_table_attached_to_owning_clause():
    table = TableModel(id="t1", page=1, rows=[["a", "b"], ["1", "2"]], header=["a", "b"])
    lines = _lines(
        ("4.2 Late Payment", 1),
        ("Penalties are shown below.", 1),
    )
    anchors = [TableAnchor(after_line_index=1, table=table)]
    doc = build_document("doc1", "test.pdf", DocType.MSA, lines, anchors, page_count=1)
    clause = next(c for c in doc.clauses if c.section_number == "4.2")
    assert "t1" in clause.table_ids
    assert doc.tables[0].id == "t1"


def test_wrapped_continuation_line_not_mistaken_for_heading():
    """A wrapped body line starting with a capitalized word (e.g. 'Schedule')
    must not be treated as a new heading -- only block-start lines can be."""
    lines = [
        Line(text="6.1 Change Order Process", page=1, is_block_start=True),
        Line(text="Any change to the scope, fees, or", page=1, is_block_start=True),
        Line(text="Schedule described in this SOW requires a change order.", page=1, is_block_start=False),
    ]
    doc = build_document("doc1", "test.pdf", DocType.SOW, lines, [], page_count=1)
    section_numbers = {c.section_number for c in doc.clauses}
    assert "Schedule described in this SOW requires a change order." not in section_numbers
    clause = next(c for c in doc.clauses if c.section_number == "6.1")
    assert "Schedule described in this SOW requires a change order." in clause.text


def test_known_vs_available_exhibit_labels():
    lines = _lines(
        ("4.3 Detailed SLA Terms", 1),
        ("See Exhibit C for details.", 1),
        ("EXHIBIT A APPROVED SUBCONTRACTORS", 2),
        ("Content of exhibit A.", 2),
    )
    doc = build_document("doc1", "test.pdf", DocType.MSA, lines, [], page_count=2)
    assert "Exhibit C" in doc.known_exhibit_labels
    assert "Exhibit A" in doc.available_exhibit_labels
    assert "Exhibit C" not in doc.available_exhibit_labels
