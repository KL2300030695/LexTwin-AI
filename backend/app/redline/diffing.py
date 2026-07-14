"""Word-level diffing between original and suggested clause text.

diff-match-patch diffs character-by-character by default, which produces
confusing sub-word fragments for legal text (e.g. diffing "forty-five" vs
"fifteen" character-by-character rather than as whole words). The standard
technique -- the same one diff-match-patch's own line-mode diffing uses
internally, applied here to words instead of lines -- is to map each unique
token to a private-use-area character, diff those synthetic strings, then
map the result back to the original tokens.
"""
from __future__ import annotations

from diff_match_patch import diff_match_patch

from app.models.redline import DiffOp, DiffOpType

# Tokenize into alternating whitespace-run / non-whitespace-run chunks, so
# concatenating tokens back together reproduces the original text exactly
# (no separator bookkeeping needed).
import re

_TOKEN_RE = re.compile(r"\s+|\S+")

# Private Use Area: plenty of headroom for a single clause's vocabulary
# (thousands of unique tokens) without colliding with real text characters.
_PUA_BASE = 0xE000
_PUA_MAX = 0xF8FF


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text)


def word_level_diff(original: str, suggested: str) -> list[DiffOp]:
    original_tokens = _tokenize(original)
    suggested_tokens = _tokenize(suggested)

    token_to_char: dict[str, str] = {}
    vocabulary: list[str] = []

    def encode(tokens: list[str]) -> str:
        chars = []
        for tok in tokens:
            char = token_to_char.get(tok)
            if char is None:
                code_point = _PUA_BASE + len(vocabulary)
                if code_point > _PUA_MAX:
                    raise ValueError("Clause text has more unique tokens than the diff encoder supports.")
                char = chr(code_point)
                token_to_char[tok] = char
                vocabulary.append(tok)
            chars.append(char)
        return "".join(chars)

    encoded_original = encode(original_tokens)
    encoded_suggested = encode(suggested_tokens)

    dmp = diff_match_patch()
    diffs = dmp.diff_main(encoded_original, encoded_suggested, checklines=False)
    dmp.diff_cleanupSemantic(diffs)

    op_type_by_code = {
        dmp.DIFF_EQUAL: DiffOpType.EQUAL,
        dmp.DIFF_INSERT: DiffOpType.INSERT,
        dmp.DIFF_DELETE: DiffOpType.DELETE,
    }

    ops: list[DiffOp] = []
    for op_code, encoded_chunk in diffs:
        text = "".join(vocabulary[ord(c) - _PUA_BASE] for c in encoded_chunk)
        if text:
            ops.append(DiffOp(type=op_type_by_code[op_code], text=text))
    return ops


def diff_to_markdown(diffs: list[DiffOp]) -> str:
    """Renders ~~deleted~~ and **inserted** markers around changed spans."""
    parts = []
    for op in diffs:
        if op.type == DiffOpType.EQUAL:
            parts.append(op.text)
        elif op.type == DiffOpType.DELETE:
            parts.append(f"~~{op.text}~~")
        elif op.type == DiffOpType.INSERT:
            parts.append(f"**{op.text}**")
    return "".join(parts)
