"""Structured-output schemas and system prompts shared by every AI provider
(Claude, Gemini, ...) -- provider-agnostic, so switching AI_PROVIDER never
changes what's being asked or how the answer is validated. Only the transport
(app/services/claude_client.py, app/services/gemini_client.py) differs."""
from __future__ import annotations

from pydantic import BaseModel, Field

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
        description="Confidence in this judgment, from 0.0 (low) to 1.0 (high).", ge=0.0, le=1.0
    )


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
