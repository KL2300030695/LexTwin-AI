"""Thin wrapper around the Claude API for the genuinely LLM-shaped parts of
this app: judging whether two same-topic clauses conflict (Phase 5), and
drafting fallback replacement language for a flagged clause (Phase 6).

Everything else (topic alignment, missing-reference gating, the word-level
diff itself) is deterministic and lives elsewhere -- this module is
intentionally small and isolated so it's easy to mock in tests without
hitting the network.
"""
from __future__ import annotations

import anthropic
from pydantic import BaseModel, Field

from app.config import settings

_SYSTEM_PROMPT = (
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


_FALLBACK_SYSTEM_PROMPT = (
    "You are a contract-review assistant drafting fallback redline language for a "
    "flagged clause. You will be given the clause's original text, the reason it was "
    "flagged as risky, and optionally a reference clause (e.g. from the governing MSA) "
    "it should be brought into alignment with. Produce a revised version of the clause "
    "that resolves the stated risk. Preserve the original wording and structure wherever "
    "possible -- make the smallest change that fixes the problem, not a full rewrite. "
    "Do not introduce new obligations beyond what's needed to resolve the flagged issue."
)


class ClaudeClientError(RuntimeError):
    """Raised when the Claude API call fails after SDK-level retries, or when
    no API key is configured. Callers should treat this as 'cannot evaluate
    right now', not as a crash."""


_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not settings.ANTHROPIC_API_KEY:
            raise ClaudeClientError(
                "ANTHROPIC_API_KEY is not configured; cannot run AI-assisted analysis."
            )
        _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


def check_contradiction(
    topic: str, msa_heading: str, msa_text: str, sow_heading: str, sow_text: str
) -> ContradictionJudgment:
    """Sends one MSA/SOW clause pair to Claude and returns a structured
    judgment. The anthropic SDK already retries connection errors, 429s, and
    5xxs with backoff (default max_retries=2); we only need to translate a
    still-failing call into our own error type."""
    client = _get_client()
    user_content = (
        f"Topic: {topic}\n\n"
        f"MSA clause ({msa_heading}):\n{msa_text}\n\n"
        f"SOW clause ({sow_heading}):\n{sow_text}\n\n"
        "Do these two clauses contradict each other?"
    )
    try:
        response = client.messages.parse(
            model=settings.CLAUDE_MODEL,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
            output_format=ContradictionJudgment,
        )
    except anthropic.APIError as e:
        raise ClaudeClientError(f"Claude API call failed: {e}") from e

    if response.parsed_output is None:
        raise ClaudeClientError("Claude response did not match the expected schema.")
    return response.parsed_output


def generate_fallback_language(
    original_heading: str, original_text: str, risk_reason: str, reference_heading: str | None, reference_text: str | None
) -> FallbackSuggestion:
    """Drafts fallback replacement text for a single flagged clause."""
    client = _get_client()
    user_content = f"Original clause ({original_heading}):\n{original_text}\n\nWhy this was flagged:\n{risk_reason}\n"
    if reference_text:
        user_content += f"\nReference clause it should align with ({reference_heading or 'reference'}):\n{reference_text}\n"
    user_content += "\nProduce a revised version of the original clause that resolves this issue."

    try:
        response = client.messages.parse(
            model=settings.CLAUDE_MODEL,
            max_tokens=1024,
            system=_FALLBACK_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
            output_format=FallbackSuggestion,
        )
    except anthropic.APIError as e:
        raise ClaudeClientError(f"Claude API call failed: {e}") from e

    if response.parsed_output is None:
        raise ClaudeClientError("Claude response did not match the expected schema.")
    return response.parsed_output
