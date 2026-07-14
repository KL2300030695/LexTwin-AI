"""Builds a 'legal playbook' seed file from the CUAD v1 dataset
(data/cuad/CUAD_v1/master_clauses.csv).

CUAD's 41 clause categories (Governing Law, Termination For Convenience, Cap
On Liability, Ip Ownership Assignment, ...) are a ready-made taxonomy of the
"topics" that Phase 5 (MSA vs SOW contradiction detection) needs to align
clauses by, and CUAD's base columns (the ones WITHOUT a "-Answer" suffix)
contain verbatim example clause language pulled from 510 real contracts --
useful as reference exemplars for playbook-driven risk rules and fallback
language suggestions later on.

Each base column's cell is a stringified Python list of verbatim text spans
(e.g. "['This Agreement is governed by the laws of Nevada...']"); the
"-Answer" columns hold a simplified value (Yes/No, or a short extracted
entity) and are NOT used here since they discard the actual clause language.

Run with: python scripts/build_cuad_playbook.py
Writes: app/playbook/cuad_playbook.json
"""
from __future__ import annotations

import ast
import csv
import json
from collections import defaultdict
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = (
    BACKEND_DIR.parent
    / "data"
    / "cuad"
    / "CUAD_v1"
    / "master_clauses.csv"
)
OUTPUT_PATH = BACKEND_DIR / "app" / "playbook" / "cuad_playbook.json"

EXAMPLES_PER_CATEGORY = 5
MAX_EXAMPLE_CHARS = 500

# Non-category metadata columns to skip (parties/dates identify the contract,
# they aren't a clause "category" to build risk rules around).
_METADATA_COLUMNS = {"Document Name", "Parties", "Agreement Date", "Effective Date", "Expiration Date"}


def _parse_cell(raw: str) -> list[str]:
    """CUAD stores each cell as a stringified Python list literal."""
    if not raw or not raw.strip():
        return []
    try:
        value = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return []
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if str(v).strip()]


def build_playbook() -> dict:
    with CSV_PATH.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    category_columns = [
        col
        for col in fieldnames
        if col != "Filename" and not col.endswith("-Answer") and col not in _METADATA_COLUMNS
    ]

    examples_by_category: dict[str, list[str]] = defaultdict(list)
    contracts_with_category: dict[str, int] = defaultdict(int)

    for row in rows:
        for category in category_columns:
            spans = _parse_cell(row.get(category, ""))
            if not spans:
                continue
            contracts_with_category[category] += 1
            for span in spans:
                if len(examples_by_category[category]) >= EXAMPLES_PER_CATEGORY:
                    break
                truncated = span if len(span) <= MAX_EXAMPLE_CHARS else span[:MAX_EXAMPLE_CHARS].rsplit(" ", 1)[0] + "..."
                if truncated not in examples_by_category[category]:
                    examples_by_category[category].append(truncated)

    categories = [
        {
            "category": category,
            "contracts_observed_in": contracts_with_category.get(category, 0),
            "total_contracts": len(rows),
            "example_clauses": examples_by_category.get(category, []),
        }
        for category in category_columns
    ]
    categories.sort(key=lambda c: -c["contracts_observed_in"])

    return {
        "source": "CUAD v1",
        "total_contracts": len(rows),
        "categories": categories,
    }


if __name__ == "__main__":
    if not CSV_PATH.exists():
        raise SystemExit(f"CUAD dataset not found at {CSV_PATH}.")
    playbook = build_playbook()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(playbook, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH} with {len(playbook['categories'])} categories from {playbook['total_contracts']} contracts")
