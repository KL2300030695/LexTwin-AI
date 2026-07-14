"""Builds a ContractNLI-derived legal playbook seed
(data/contract_nli/contract-nli/{train,dev,test}.json).

ContractNLI is 607 real NDAs annotated against 17 fixed hypotheses (e.g.
"Receiving Party shall not disclose the fact that Agreement was agreed or
negotiated.", "Some obligations of Agreement may survive termination.") with
a document-level label of Entailment / Contradiction / NotMentioned plus
cited evidence spans. The 17 hypotheses read as a ready-made confidentiality
/ NDA risk checklist -- used here as a new playbook category set (one
category per hypothesis) with verbatim Entailment evidence spans as
examples of what satisfying language looks like. Browsable reference only
(see app/playbook/__init__.py), not wired into live topic-alignment.

Run with: python scripts/build_contractnli_playbook.py
Writes: app/playbook/contractnli_playbook.json
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BACKEND_DIR.parent / "data" / "contract_nli" / "contract-nli"
OUTPUT_PATH = BACKEND_DIR / "app" / "playbook" / "contractnli_playbook.json"

EXAMPLES_PER_CATEGORY = 5
MAX_EXAMPLE_CHARS = 500
SPLITS = ("train.json", "dev.json", "test.json")


def _evidence_text(doc: dict, span_indices: list[int]) -> str:
    spans = doc["spans"]
    pieces = []
    for idx in span_indices:
        start, end = spans[idx]
        pieces.append(doc["text"][start:end].strip())
    joined = " ... ".join(p for p in pieces if p)
    return joined if len(joined) <= MAX_EXAMPLE_CHARS else joined[:MAX_EXAMPLE_CHARS].rsplit(" ", 1)[0] + "..."


def build_playbook() -> dict:
    short_descriptions: dict[str, str] = {}
    hypothesis_texts: dict[str, str] = {}
    counts: dict[str, int] = defaultdict(int)
    examples: dict[str, list[str]] = defaultdict(list)
    total_docs = 0

    for split_file in SPLITS:
        path = DATASET_DIR / split_file
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for key, label in data["labels"].items():
            short_descriptions[key] = label["short_description"]
            hypothesis_texts[key] = label["hypothesis"]

        for doc in data["documents"]:
            total_docs += 1
            annotations = doc["annotation_sets"][0]["annotations"]
            for key, annotation in annotations.items():
                if annotation["choice"] != "Entailment":
                    continue
                counts[key] += 1
                if len(examples[key]) >= EXAMPLES_PER_CATEGORY:
                    continue
                text = _evidence_text(doc, annotation["spans"])
                if text and text not in examples[key]:
                    examples[key].append(text)

    categories = [
        {
            "category": short_descriptions[key],
            "hypothesis": hypothesis_texts[key],
            "example_count": counts.get(key, 0),
            "total_examples": total_docs,
            "example_clauses": examples.get(key, []),
        }
        for key in sorted(short_descriptions, key=lambda k: -counts.get(k, 0))
    ]

    return {"source": "ContractNLI", "total_examples": total_docs, "categories": categories}


if __name__ == "__main__":
    if not DATASET_DIR.exists():
        raise SystemExit(f"ContractNLI dataset not found at {DATASET_DIR}.")
    playbook = build_playbook()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(playbook, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH} with {len(playbook['categories'])} hypotheses from {playbook['total_examples']} NDAs")
