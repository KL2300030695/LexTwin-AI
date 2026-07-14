from app.models.redline import DiffOpType
from app.redline.diffing import diff_to_markdown, word_level_diff


def _reconstruct(diffs, keep_types):
    return "".join(op.text for op in diffs if op.type in keep_types)


def test_identical_text_produces_single_equal_op():
    diffs = word_level_diff("Client shall pay within fifteen days.", "Client shall pay within fifteen days.")
    assert len(diffs) == 1
    assert diffs[0].type == DiffOpType.EQUAL


def test_word_substitution_isolates_the_changed_word():
    diffs = word_level_diff(
        "Client shall pay invoices within fifteen days of receipt.",
        "Client shall pay invoices within forty-five days of receipt.",
    )
    deletes = [op.text for op in diffs if op.type == DiffOpType.DELETE]
    inserts = [op.text for op in diffs if op.type == DiffOpType.INSERT]
    assert deletes == ["fifteen"]
    assert inserts == ["forty-five"]
    # surrounding text should be marked equal, not re-diffed character by character
    equal_text = "".join(op.text for op in diffs if op.type == DiffOpType.EQUAL)
    assert "Client shall pay invoices within" in equal_text
    assert "days of receipt." in equal_text


def test_reconstructing_original_and_suggested_from_diff_ops():
    original = "Payment within ninety days."
    suggested = "Payment within thirty days."
    diffs = word_level_diff(original, suggested)

    reconstructed_original = _reconstruct(diffs, {DiffOpType.EQUAL, DiffOpType.DELETE})
    reconstructed_suggested = _reconstruct(diffs, {DiffOpType.EQUAL, DiffOpType.INSERT})
    assert reconstructed_original == original
    assert reconstructed_suggested == suggested


def test_pure_insertion():
    diffs = word_level_diff("The fee is due.", "The fee is due within thirty days.")
    inserts = [op.text for op in diffs if op.type == DiffOpType.INSERT]
    assert any("thirty" in t for t in inserts)


def test_pure_deletion():
    diffs = word_level_diff("The fee is due within thirty days.", "The fee is due.")
    deletes = [op.text for op in diffs if op.type == DiffOpType.DELETE]
    assert any("thirty" in t for t in deletes)


def test_whitespace_and_punctuation_preserved_exactly():
    original = "Section 5.1:  pay within 45 days."
    diffs = word_level_diff(original, original)
    assert "".join(op.text for op in diffs) == original


def test_diff_to_markdown_renders_strikethrough_and_bold():
    diffs = word_level_diff("Payment within ninety days.", "Payment within thirty days.")
    md = diff_to_markdown(diffs)
    assert "~~ninety~~" in md
    assert "**thirty**" in md
    assert "Payment within" in md


def test_empty_strings():
    assert word_level_diff("", "") == []
