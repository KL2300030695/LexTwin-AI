"""Builds a LEDGAR-derived legal playbook seed
(data/ledgar/ledgar/{train,validation,test}-00000-of-00001.parquet).

LEDGAR (a sub-task of the LexGLUE benchmark) is 60k individual contract
provisions, each single-labeled with one of 100 clause categories
(Indemnifications, Non-Disparagement, Survival, Warranties, Governing Laws,
...) -- a much larger and more fine-grained clause taxonomy than CUAD's 41
categories. Used here purely as browsable reference examples in the
playbook UI (see app/playbook/__init__.py) -- it is NOT wired into the
live topic-alignment config used for contradiction detection, to avoid
silently changing analysis cost/behavior; users can promote any of these
categories into their topic rules via the Playbook page if they want.

Run with: python scripts/build_ledgar_playbook.py
Writes: app/playbook/ledgar_playbook.json
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BACKEND_DIR.parent / "data" / "ledgar" / "ledgar"
OUTPUT_PATH = BACKEND_DIR / "app" / "playbook" / "ledgar_playbook.json"

EXAMPLES_PER_CATEGORY = 5
MAX_EXAMPLE_CHARS = 500
SPLITS = ("train", "validation", "test")


def _label_names(table: pq.Table) -> list[str]:
    meta = json.loads(table.schema.metadata[b"huggingface"])
    return meta["info"]["features"]["label"]["names"]


def build_playbook() -> dict:
    tables = [pq.read_table(DATASET_DIR / f"{split}-00000-of-00001.parquet") for split in SPLITS]
    label_names = _label_names(tables[0])

    counts: dict[str, int] = defaultdict(int)
    examples: dict[str, list[str]] = defaultdict(list)
    total = 0

    for table in tables:
        columns = table.to_pydict()
        for text, label_id in zip(columns["text"], columns["label"]):
            total += 1
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

    return {"source": "LEDGAR (LexGLUE)", "total_examples": total, "categories": categories}


if __name__ == "__main__":
    if not DATASET_DIR.exists():
        raise SystemExit(f"LEDGAR dataset not found at {DATASET_DIR}.")
    playbook = build_playbook()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(playbook, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH} with {len(playbook['categories'])} categories from {playbook['total_examples']} labeled examples")
