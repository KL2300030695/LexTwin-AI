"""Builds an unfair_tos-derived legal playbook seed
(data/ledgar/unfair_tos/{train,validation,test}-00000-of-00001.parquet).

unfair_tos (a sub-task of the LexGLUE benchmark) is ~5.5k Terms-of-Service
sentences, each multi-labeled with 0+ of 8 "potentially unfair clause"
categories (Limitation of liability, Unilateral termination, Unilateral
change, Arbitration, ...). Consumer ToS phrasing differs from B2B MSA/SOW
language, but the category taxonomy is directly relevant to risk-flagging.
Used purely as browsable reference examples (see app/playbook/__init__.py),
not wired into live topic-alignment/risk-flag generation.

Run with: python scripts/build_unfair_tos_playbook.py
Writes: app/playbook/unfair_tos_playbook.json
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BACKEND_DIR.parent / "data" / "ledgar" / "unfair_tos"
OUTPUT_PATH = BACKEND_DIR / "app" / "playbook" / "unfair_tos_playbook.json"

EXAMPLES_PER_CATEGORY = 5
MAX_EXAMPLE_CHARS = 500
SPLITS = ("train", "validation", "test")


def _label_names(table: pq.Table) -> list[str]:
    meta = json.loads(table.schema.metadata[b"huggingface"])
    return meta["info"]["features"]["labels"]["feature"]["names"]


def build_playbook() -> dict:
    tables = [pq.read_table(DATASET_DIR / f"{split}-00000-of-00001.parquet") for split in SPLITS]
    label_names = _label_names(tables[0])

    counts: dict[str, int] = defaultdict(int)
    examples: dict[str, list[str]] = defaultdict(list)
    total = 0

    for table in tables:
        columns = table.to_pydict()
        for text, label_ids in zip(columns["text"], columns["labels"]):
            total += 1
            for label_id in label_ids:
                category = label_names[label_id]
                counts[category] += 1
                if len(examples[category]) >= EXAMPLES_PER_CATEGORY:
                    continue
                truncated = text if len(text) <= MAX_EXAMPLE_CHARS else text[:MAX_EXAMPLE_CHARS].rsplit(" ", 1)[0] + "..."
                if truncated not in examples[category]:
                    examples[category].append(truncated)

    categories = [
        {
            "category": name,
            "example_count": counts.get(name, 0),
            "total_examples": total,
            "example_clauses": examples.get(name, []),
        }
        for name in label_names
    ]
    categories.sort(key=lambda c: -c["example_count"])

    return {"source": "Unfair ToS (LexGLUE)", "total_examples": total, "categories": categories}


if __name__ == "__main__":
    if not DATASET_DIR.exists():
        raise SystemExit(f"unfair_tos dataset not found at {DATASET_DIR}.")
    playbook = build_playbook()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(playbook, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH} with {len(playbook['categories'])} categories from {playbook['total_examples']} labeled examples")
