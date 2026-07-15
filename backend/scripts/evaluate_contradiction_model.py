"""Evaluates the local contradiction-judgment model (Qwen2.5-7B via
app/services/local_llm_client.py) against ContractNLI's real, human-annotated
entailment/contradiction labels (Koreeda & Manning, EMNLP Findings 2021).

This is NOT an evaluation of the exact production MSA/SOW contradiction
prompt -- CONTRADICTION_SYSTEM_PROMPT in app/services/ai_schemas.py is
hardcoded to "MSA clause vs SOW clause" framing, which would misdescribe NDA
content. It evaluates the same underlying model + grammar-constrained JSON
schema mechanism (local_llm_client._structured_chat_completion) with a
generic contradiction-vs-entailment prompt appropriate to ContractNLI's
actual task shape: does a contract clause CONTRADICT or ENTAIL (support) a
claimed hypothesis statement about it?

Uses ContractNLI's gold evidence spans as the premise text (the "oracle
evidence" setting used in the ContractNLI paper itself), not full-document
retrieval -- this isolates the judgment task from a separate retrieval
problem this script doesn't attempt to solve, and keeps each example's
context short enough for reasonably fast local inference.

NotMentioned-labeled examples are excluded: there is no textual evidence to
call them a contradiction or a non-contradiction one way or the other.

Usage:
    python scripts/evaluate_contradiction_model.py [--n-per-class 12] [--seed 0]

Each example is one local-model inference call (slow -- see README
Performance section), so this is a deliberately small, stratified sample,
not a full-dataset benchmark run.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.ai_schemas import ContradictionJudgment  # noqa: E402
from app.services.local_llm_client import LocalLLMClientError, _structured_chat_completion  # noqa: E402

DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "contract_nli" / "contract-nli" / "test.json"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "eval_results" / "contractnli_contradiction_eval.json"

GENERIC_SYSTEM_PROMPT = (
    "You are a contract-review assistant. You will be given an excerpt from a real "
    "contract clause and a statement someone has made about what that clause says. "
    "Decide whether the clause CONTRADICTS the statement (the clause says the opposite, "
    "or something clearly incompatible with it) or ENTAILS/SUPPORTS the statement (the "
    "clause's content backs up or is consistent with the statement). Judge only based on "
    "the clause text given -- do not assume facts not stated in it."
)
# A prior experiment added explicit "definitional carve-out" guidance here
# (e.g. "a clause excluding independently-developed info from the
# Confidential Information definition ENTAILS, not contradicts, a statement
# that such development is permitted"). It fixed the exact false-positive
# pattern it targeted (precision 0.77 -> 0.90) but the longer, more elaborate
# explanations it produced triggered a real, separate failure mode: 6 of 24
# examples (25%) came back with a raw unescaped control character inside the
# model's JSON string output, failing Pydantic validation even under
# grammar-constrained decoding. Not adopted -- see
# eval_results/contractnli_contradiction_eval_carveout_experiment.json and
# the README's Model Evaluation section for the full before/after numbers.


def build_examples(data: dict, n_per_class: int, seed: int) -> list[dict]:
    by_choice: dict[str, list[dict]] = {"Contradiction": [], "Entailment": []}
    for doc in data["documents"]:
        text = doc["text"]
        spans = doc["spans"]
        for hyp_id, ann in doc["annotation_sets"][0]["annotations"].items():
            choice = ann["choice"]
            if choice not in by_choice or not ann["spans"]:
                continue
            evidence = " ".join(text[spans[i][0]:spans[i][1]] for i in ann["spans"])
            by_choice[choice].append(
                {
                    "doc_file": doc["file_name"],
                    "hypothesis_id": hyp_id,
                    "hypothesis": data["labels"][hyp_id]["hypothesis"],
                    "clause_excerpt": evidence,
                    "ground_truth_has_contradiction": choice == "Contradiction",
                }
            )

    rng = random.Random(seed)
    examples = []
    for choice in ("Contradiction", "Entailment"):
        pool = by_choice[choice]
        rng.shuffle(pool)
        examples.extend(pool[:n_per_class])
    rng.shuffle(examples)
    return examples


def run_eval(examples: list[dict]) -> list[dict]:
    results = []
    for i, ex in enumerate(examples, 1):
        user_content = (
            f"Contract clause excerpt:\n{ex['clause_excerpt']}\n\n"
            f"Statement: {ex['hypothesis']}\n\n"
            "Does the clause contradict or entail this statement?"
        )
        start = time.time()
        try:
            raw = _structured_chat_completion(GENERIC_SYSTEM_PROMPT, user_content, ContradictionJudgment)
            judgment = ContradictionJudgment.model_validate_json(raw)
            predicted = judgment.has_contradiction
            error = None
            explanation = judgment.explanation
            confidence = judgment.confidence
        except (LocalLLMClientError, ValueError) as e:
            # ValueError covers pydantic's ValidationError (a ValueError
            # subclass) from model_validate_json -- e.g. the model
            # occasionally emits a literal unescaped control character inside
            # a JSON string, which is invalid JSON despite grammar
            # constraints. One bad example shouldn't crash the whole run.
            predicted = None
            error = str(e)
            explanation = None
            confidence = None
        elapsed = time.time() - start

        result = {
            **ex,
            "predicted_has_contradiction": predicted,
            "confidence": confidence,
            "explanation": explanation,
            "error": error,
            "elapsed_seconds": round(elapsed, 1),
        }
        results.append(result)
        status = "ERROR" if error else ("CORRECT" if predicted == ex["ground_truth_has_contradiction"] else "WRONG")
        print(
            f"[{i}/{len(examples)}] {ex['hypothesis_id']} truth={ex['ground_truth_has_contradiction']} "
            f"pred={predicted} ({status}) {elapsed:.0f}s",
            flush=True,
        )
    return results


def compute_metrics(results: list[dict]) -> dict:
    valid = [r for r in results if r["predicted_has_contradiction"] is not None]
    tp = sum(1 for r in valid if r["ground_truth_has_contradiction"] and r["predicted_has_contradiction"])
    fp = sum(1 for r in valid if not r["ground_truth_has_contradiction"] and r["predicted_has_contradiction"])
    tn = sum(1 for r in valid if not r["ground_truth_has_contradiction"] and not r["predicted_has_contradiction"])
    fn = sum(1 for r in valid if r["ground_truth_has_contradiction"] and not r["predicted_has_contradiction"])

    accuracy = (tp + tn) / len(valid) if valid else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    return {
        "n_total": len(results),
        "n_valid": len(valid),
        "n_errors": len(results) - len(valid),
        "confusion_matrix": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-per-class", type=int, default=12)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    examples = build_examples(data, args.n_per_class, args.seed)
    print(f"Evaluating {len(examples)} examples ({args.n_per_class} per class) from ContractNLI's test split...")

    results = run_eval(examples)
    metrics = compute_metrics(results)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"metrics": metrics, "results": results}, f, indent=2)

    print("\n=== Metrics ===")
    print(json.dumps(metrics, indent=2))
    print(f"\nFull results written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
