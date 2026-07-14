"""Hand-built Clause/ParsedDocument fixtures for precise control over
modal-verb detection, permissive-language exclusion, and deadline parsing.
See test_obligation_integration.py for checks against the real sample
contracts."""
from app.models.schema import Clause, DocType, ParsedDocument
from app.obligations.extractor import extract_obligations


def _clause(section_number: str | None, text: str, doc_id: str = "d1") -> Clause:
    return Clause(
        id=f"{doc_id}::{section_number}",
        doc_id=doc_id,
        doc_type=DocType.MSA,
        section_number=section_number,
        parent_section=None,
        level=1,
        heading=f"Clause {section_number}",
        text=text,
        page_start=3,
        page_end=3,
    )


def _doc(clauses: list[Clause], doc_id: str = "d1") -> ParsedDocument:
    return ParsedDocument(doc_id=doc_id, filename=f"{doc_id}.pdf", doc_type=DocType.MSA, clauses=clauses)


def test_shall_is_detected_as_an_obligation():
    doc = _doc([_clause("5.1", "Client shall pay all undisputed invoices within thirty days.")])
    obligations = extract_obligations(doc)
    assert len(obligations) == 1
    assert obligations[0].obligation_verb.lower() == "shall"


def test_must_is_detected_as_an_obligation():
    doc = _doc([_clause("2.1", "Provider must maintain valid insurance coverage.")])
    obligations = extract_obligations(doc)
    assert len(obligations) == 1
    assert obligations[0].obligation_verb.lower() == "must"


def test_agrees_to_is_detected_as_an_obligation():
    doc = _doc([_clause("2.2", "Provider agrees to maintain a data protection policy.")])
    obligations = extract_obligations(doc)
    assert len(obligations) == 1
    assert obligations[0].obligation_verb.lower() == "agrees to"


def test_will_is_detected_as_an_obligation():
    doc = _doc([_clause("1.1", "Provider will migrate the workloads to the cloud.")])
    obligations = extract_obligations(doc)
    assert len(obligations) == 1
    assert obligations[0].obligation_verb.lower() == "will"


def test_may_is_permissive_and_excluded():
    """'may' grants a right/option, not an obligation -- must never surface
    as an obligation, even though it's a modal verb in the same family."""
    doc = _doc([_clause("8.1", "Either party may terminate this Agreement for convenience upon notice.")])
    obligations = extract_obligations(doc)
    assert obligations == []


def test_mixed_sentences_only_obligation_ones_extracted():
    text = (
        "Provider may suspend the Services at its discretion. "
        "Client shall pay all fees within fifteen days of invoice."
    )
    doc = _doc([_clause("5.2", text)])
    obligations = extract_obligations(doc)
    assert len(obligations) == 1
    assert "Client shall pay" in obligations[0].text


def test_numeric_deadline_extracted():
    doc = _doc([_clause("5.1", "Client shall pay all invoices within 30 days of receipt.")])
    obligations = extract_obligations(doc)
    assert obligations[0].deadline_days == 30


def test_spelled_out_deadline_extracted():
    doc = _doc([_clause("5.1", "Client shall pay all undisputed invoices within forty-five days of receipt.")])
    obligations = extract_obligations(doc)
    assert obligations[0].deadline_days == 45


def test_single_word_spelled_out_deadline_extracted():
    doc = _doc([_clause("3.3", "Client shall pay invoices within fifteen days of receipt.")])
    obligations = extract_obligations(doc)
    assert obligations[0].deadline_days == 15


def test_have_n_days_pattern_extracted():
    doc = _doc([_clause("7.1", "Client shall have ten business days to review each Deliverable.")])
    obligations = extract_obligations(doc)
    assert obligations[0].deadline_days == 10


def test_no_later_than_pattern_extracted():
    doc = _doc([_clause("9.1", "Provider shall remediate the defect no later than 5 days after notice.")])
    obligations = extract_obligations(doc)
    assert obligations[0].deadline_days == 5


def test_sentence_without_deadline_leaves_deadline_fields_none():
    doc = _doc([_clause("7.1", "Each party shall protect the other party's Confidential Information.")])
    obligations = extract_obligations(doc)
    assert obligations[0].deadline_text is None
    assert obligations[0].deadline_days is None


def test_responsible_party_best_effort_extraction():
    doc = _doc([_clause("5.1", "Client shall pay all undisputed invoices within thirty days of receipt.")])
    obligations = extract_obligations(doc)
    assert obligations[0].responsible_party is not None
    assert "Client" in obligations[0].responsible_party


def test_clause_without_section_number_excluded():
    preamble = Clause(
        id="d1::preamble", doc_id="d1", doc_type=DocType.MSA, section_number=None,
        parent_section=None, level=0, heading="Preamble",
        text="Client shall pay the Provider promptly.", page_start=1, page_end=1,
    )
    doc = _doc([preamble])
    assert extract_obligations(doc) == []


def test_clause_with_empty_text_excluded():
    doc = _doc([_clause("2.1", "")])
    assert extract_obligations(doc) == []


def test_multiple_obligations_in_same_clause_get_distinct_ids():
    text = "Provider shall invoice Client monthly in arrears. Client shall pay all undisputed invoices within forty-five days of receipt."
    doc = _doc([_clause("5.1", text)])
    obligations = extract_obligations(doc)
    assert len(obligations) == 2
    assert obligations[0].id != obligations[1].id
    assert all(o.clause_id == "d1::5.1" for o in obligations)


def test_obligation_carries_page_and_heading_from_clause():
    clause = _clause("6.2", "Neither party shall be liable for indirect damages.")
    doc = _doc([clause])
    obligations = extract_obligations(doc)
    assert obligations[0].page == 3
    assert obligations[0].heading == "Clause 6.2"
    assert obligations[0].section_number == "6.2"
    assert obligations[0].doc_id == "d1"
