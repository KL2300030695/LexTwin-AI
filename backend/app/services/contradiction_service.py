"""Phase 5: cross-document (MSA vs SOW) contradiction detection.

Pipeline: align clauses by topic (deterministic, app/contradiction), skip any
pair where either clause is blocked by the Phase 4 missing-reference check
(refuse to evaluate rather than guess), then ask Claude to judge the
remaining pairs (app/services/claude_client).
"""
from __future__ import annotations

from app.completeness import check_completeness
from app.contradiction.topic_alignment import align_clauses
from app.models.contradiction import ContradictionAnalysis, ContradictionResult, ContradictionStatus
from app.services.claude_client import ClaudeClientError, check_contradiction
from app.services.document_service import get_document


def _load_pair(msa_doc_id: str, sow_doc_id: str):
    msa = get_document(msa_doc_id)
    if msa is None:
        raise ValueError(f"Document not found: {msa_doc_id}")
    sow = get_document(sow_doc_id)
    if sow is None:
        raise ValueError(f"Document not found: {sow_doc_id}")
    return msa, sow


def analyze_contradictions(msa_doc_id: str, sow_doc_id: str) -> ContradictionAnalysis:
    msa, sow = _load_pair(msa_doc_id, sow_doc_id)

    completeness = check_completeness([msa, sow])
    status_by_clause_id = {s.clause_id: s for s in completeness.clause_statuses}

    pairs = align_clauses(msa, sow)
    results: list[ContradictionResult] = []

    for pair in pairs:
        msa_status = status_by_clause_id.get(pair.msa_clause.id)
        sow_status = status_by_clause_id.get(pair.sow_clause.id)
        blocked_reasons = [
            s.reason for s in (msa_status, sow_status) if s is not None and not s.can_evaluate and s.reason
        ]
        if blocked_reasons:
            results.append(
                ContradictionResult(
                    topic=pair.topic,
                    msa_clause_id=pair.msa_clause.id,
                    sow_clause_id=pair.sow_clause.id,
                    status=ContradictionStatus.CANNOT_EVALUATE,
                    reason="; ".join(blocked_reasons),
                )
            )
            continue

        try:
            judgment = check_contradiction(
                topic=pair.topic,
                msa_heading=pair.msa_clause.heading or pair.msa_clause.section_number or "",
                msa_text=pair.msa_clause.text,
                sow_heading=pair.sow_clause.heading or pair.sow_clause.section_number or "",
                sow_text=pair.sow_clause.text,
            )
        except ClaudeClientError as e:
            results.append(
                ContradictionResult(
                    topic=pair.topic,
                    msa_clause_id=pair.msa_clause.id,
                    sow_clause_id=pair.sow_clause.id,
                    status=ContradictionStatus.ERROR,
                    reason=str(e),
                )
            )
            continue

        results.append(
            ContradictionResult(
                topic=pair.topic,
                msa_clause_id=pair.msa_clause.id,
                sow_clause_id=pair.sow_clause.id,
                status=ContradictionStatus.ANALYZED,
                has_contradiction=judgment.has_contradiction,
                explanation=judgment.explanation,
                confidence=judgment.confidence,
            )
        )

    contradictions_found = sum(
        1 for r in results if r.status == ContradictionStatus.ANALYZED and r.has_contradiction
    )

    return ContradictionAnalysis(
        msa_doc_id=msa_doc_id,
        sow_doc_id=sow_doc_id,
        results=results,
        contradictions_found=contradictions_found,
    )
