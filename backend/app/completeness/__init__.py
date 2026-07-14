"""Missing-reference / refusal check (Phase 4).

'If a clause references an exhibit, appendix, or external document that
hasn't been uploaded, flag that clause as "cannot evaluate - missing
reference" instead of analyzing it.'

This is doc-SET-aware, not per-document: a SOW's reference to "Exhibit A"
is only missing if Exhibit A's content isn't present anywhere in the set of
documents being analyzed together (Exhibit A commonly lives in the MSA, not
the SOW itself). Phase 5 (LLM contradiction detection) must skip clauses
flagged here rather than asking the model to reason about content it was
never given.
"""
from __future__ import annotations

from app.graph.reference_resolution import (
    DOCTYPE_TO_EXTERNAL_DOC_LABEL,
    qualifying_external_doctype,
    resolve_external_doctype,
)
from app.models.completeness import (
    ClauseEvaluationStatus,
    CompletenessAnalysis,
    MissingReference,
    MissingReferenceType,
)
from app.models.schema import Clause, DocType, ParsedDocument, ReferenceType

_EXHIBIT_LIKE_TYPES = {
    ReferenceType.EXHIBIT: MissingReferenceType.EXHIBIT,
    ReferenceType.APPENDIX: MissingReferenceType.APPENDIX,
    ReferenceType.ANNEXURE: MissingReferenceType.ANNEXURE,
    ReferenceType.SCHEDULE: MissingReferenceType.SCHEDULE,
}


def _missing_references_for_clause(
    clause: Clause,
    available_doc_types: set[DocType],
    available_exhibit_labels: set[str],
) -> list[MissingReference]:
    missing: dict[tuple[MissingReferenceType, str], MissingReference] = {}

    for ref in clause.references:
        if ref.type in _EXHIBIT_LIKE_TYPES and ref.target_label:
            if ref.target_label not in available_exhibit_labels:
                key = (_EXHIBIT_LIKE_TYPES[ref.type], ref.target_label)
                missing[key] = MissingReference(
                    label=ref.target_label,
                    type=_EXHIBIT_LIKE_TYPES[ref.type],
                    raw_text=ref.raw_text,
                    context=ref.context,
                )

        elif ref.type == ReferenceType.EXTERNAL_DOC and ref.target_label:
            mapped_doctype = resolve_external_doctype(ref.target_label)
            if mapped_doctype is not None and mapped_doctype not in available_doc_types:
                key = (MissingReferenceType.EXTERNAL_DOCUMENT, ref.target_label)
                missing[key] = MissingReference(
                    label=ref.target_label,
                    type=MissingReferenceType.EXTERNAL_DOCUMENT,
                    raw_text=ref.raw_text,
                    context=ref.context,
                )

        elif ref.type == ReferenceType.SECTION and ref.target_section:
            redirect_doctype = qualifying_external_doctype(clause, ref)
            if redirect_doctype is not None and redirect_doctype not in available_doc_types:
                doc_label = DOCTYPE_TO_EXTERNAL_DOC_LABEL.get(redirect_doctype, redirect_doctype.value)
                label = f"Section {ref.target_section} ({doc_label})"
                key = (MissingReferenceType.EXTERNAL_DOCUMENT, label)
                missing[key] = MissingReference(
                    label=label,
                    type=MissingReferenceType.EXTERNAL_DOCUMENT,
                    raw_text=ref.raw_text,
                    context=ref.context,
                )

    return list(missing.values())


def check_completeness(documents: list[ParsedDocument]) -> CompletenessAnalysis:
    available_doc_types = {doc.doc_type for doc in documents}
    available_exhibit_labels: set[str] = set()
    for doc in documents:
        available_exhibit_labels.update(doc.available_exhibit_labels)

    clause_statuses: list[ClauseEvaluationStatus] = []
    blocked_count = 0
    total_count = 0

    for doc in documents:
        for clause in doc.clauses:
            if not clause.section_number:
                continue
            total_count += 1

            missing = _missing_references_for_clause(clause, available_doc_types, available_exhibit_labels)
            can_evaluate = len(missing) == 0
            reason = None
            if not can_evaluate:
                blocked_count += 1
                labels = ", ".join(m.label for m in missing)
                reason = f"Cannot evaluate -- missing reference(s): {labels}"

            clause_statuses.append(
                ClauseEvaluationStatus(
                    clause_id=clause.id,
                    doc_id=doc.doc_id,
                    section_number=clause.section_number,
                    can_evaluate=can_evaluate,
                    missing_references=missing,
                    reason=reason,
                )
            )

    return CompletenessAnalysis(
        analyzed_doc_ids=[doc.doc_id for doc in documents],
        available_doc_types=sorted(available_doc_types, key=lambda d: d.value),
        available_exhibit_labels=sorted(available_exhibit_labels),
        clause_statuses=clause_statuses,
        blocked_clause_count=blocked_count,
        total_clause_count=total_count,
    )
