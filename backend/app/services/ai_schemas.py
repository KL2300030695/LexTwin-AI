"""Structured-output schemas and system prompts for the local LLM
(app/services/local_llm_client.py). Kept as a separate module (rather than
inline in the client) so the prompt/schema contract is the single place
that changes if the model or its structured-output mechanism ever does.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

CONTRADICTION_SYSTEM_PROMPT = (
    "You are a contract-review assistant comparing a clause in a Master Service "
    "Agreement (MSA) against the corresponding clause in a Statement of Work "
    "(SOW) issued under that MSA. Both clauses are about the same topic. "
    "Decide whether they impose materially conflicting obligations, terms, or "
    "durations on the parties (e.g. different payment deadlines, different "
    "liability caps, different service levels for the same metric). Minor "
    "wording differences, or a SOW clause that adds detail without conflicting "
    "with the MSA, are NOT contradictions."
)


class ContradictionJudgment(BaseModel):
    has_contradiction: bool = Field(
        description="Whether the two clauses impose materially conflicting obligations or terms."
    )
    explanation: str = Field(
        description="One to two sentence explanation of why they conflict, or why they don't."
    )
    confidence: float = Field(
        description=(
            "Confidence in this judgment, as a DECIMAL FRACTION between 0.0 (low) and 1.0 (high) -- "
            "e.g. 0.9 for high confidence. NOT a percentage: do not write 90, write 0.9."
        ),
        ge=0.0,
        le=1.0,
    )

    @field_validator("confidence", mode="before")
    @classmethod
    def _normalize_percentage_confidence(cls, value: float) -> float:
        """Grammar-constrained local-model decoding enforces JSON *shape*
        (valid number, required field) but not numeric-range semantics like
        Pydantic's ge=0/le=1 -- verified directly: despite an explicit 0.0-1.0
        instruction in both the prompt and this field's own description, a
        real run returned confidence: 100. Treat any value over 1 as a
        0-100 percentage the model used instead, then clamp defensively."""
        if isinstance(value, (int, float)) and value > 1:
            value = value / 100
        return max(0.0, min(1.0, value))


class FallbackSuggestion(BaseModel):
    suggested_text: str = Field(
        description=(
            "A revised version of the original clause that resolves the stated risk. "
            "Preserve the original clause's structure and wording as much as possible -- "
            "change only what's necessary to resolve the issue, so the difference from "
            "the original is minimal and easy to review."
        )
    )
    rationale: str = Field(description="One or two sentence explanation of what changed and why.")


FALLBACK_SYSTEM_PROMPT = (
    "You are a contract-review assistant drafting fallback redline language for a "
    "flagged clause. You will be given the clause's original text, the reason it was "
    "flagged as risky, and optionally a reference clause (e.g. from the governing MSA) "
    "it should be brought into alignment with. Produce a revised version of the clause "
    "that resolves the stated risk. Preserve the original wording and structure wherever "
    "possible -- make the smallest change that fixes the problem, not a full rewrite. "
    "Do not introduce new obligations beyond what's needed to resolve the flagged issue."
)


def contradiction_user_content(topic: str, msa_heading: str, msa_text: str, sow_heading: str, sow_text: str) -> str:
    return (
        f"Topic: {topic}\n\n"
        f"MSA clause ({msa_heading}):\n{msa_text}\n\n"
        f"SOW clause ({sow_heading}):\n{sow_text}\n\n"
        "Do these two clauses contradict each other?"
    )


def fallback_user_content(
    original_heading: str, original_text: str, risk_reason: str, reference_heading: str | None, reference_text: str | None
) -> str:
    content = f"Original clause ({original_heading}):\n{original_text}\n\nWhy this was flagged:\n{risk_reason}\n"
    if reference_text:
        content += f"\nReference clause it should align with ({reference_heading or 'reference'}):\n{reference_text}\n"
    content += "\nProduce a revised version of the original clause that resolves this issue."
    return content


CHAT_SYSTEM_PROMPT = (
    "You are a contract-review assistant answering questions about an MSA (Master Service "
    "Agreement) and its SOW (Statement of Work). You will be given a numbered list of contract "
    "clauses retrieved as relevant to the question, and the question itself. Answer using ONLY "
    "the provided clauses -- do not use outside knowledge or assume facts not stated in them. If "
    "the provided clauses don't contain enough information to answer, say so explicitly rather "
    "than guessing. Report which clauses you relied on ONLY in the cited_refs field, as their "
    "reference numbers -- do NOT write bracketed reference numbers like '[1]' inline in the answer "
    "text itself; the answer text should read as plain, natural prose with no citation markers, "
    "since citations are rendered separately by the app."
)


class ChatAnswer(BaseModel):
    answer: str = Field(description="Answer to the question, grounded only in the provided context clauses.")
    cited_refs: list[int] = Field(
        default_factory=list,
        description="The [N] reference numbers of the context clauses actually used to produce the answer.",
    )


def chat_user_content(context_block: str, history_block: str, question: str) -> str:
    parts = [f"Context clauses:\n{context_block}" if context_block else "Context clauses: (none retrieved)"]
    if history_block:
        parts.append(f"Prior conversation:\n{history_block}")
    parts.append(f"Question: {question}")
    return "\n\n".join(parts)
