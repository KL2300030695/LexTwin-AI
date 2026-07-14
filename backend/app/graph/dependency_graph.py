"""Builds the clause dependency graph: nodes are clauses, edges are the
section cross-references found by app.parsers.reference_extractor.

This is deliberately NOT an LLM step -- reference resolution, cycle
detection, and "Notwithstanding" precedence are all graph/regex logic so the
result is reproducible and explainable (every edge traces back to an exact
raw_text span in the source clause).
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

import networkx as nx

from app.models.graph import (
    CircularReferenceGroup,
    GeneralOverride,
    GraphAnalysis,
    GraphEdge,
    GraphNode,
    NotwithstandingOverride,
    UnresolvedReference,
)
from app.graph.reference_resolution import qualifying_external_doctype
from app.models.schema import Clause, DocType, ParsedDocument, Reference, ReferenceType

_GENERAL_OVERRIDE_SNIPPET_RE = re.compile(r"Notwithstanding.{0,150}", re.IGNORECASE | re.DOTALL)


@dataclass
class ClauseGraphResult:
    graph: nx.DiGraph
    analysis: GraphAnalysis


def _resolve_section_reference(
    doc: ParsedDocument,
    clause: Clause,
    ref: Reference,
    clauses_by_doc: dict[str, dict[str, Clause]],
    docs_by_type: dict[DocType, list[ParsedDocument]],
) -> tuple[str, Clause] | tuple[None, None]:
    redirect_doctype = qualifying_external_doctype(clause, ref)

    if redirect_doctype is not None and redirect_doctype != doc.doc_type:
        for other_doc in docs_by_type.get(redirect_doctype, []):
            if other_doc.doc_id == doc.doc_id:
                continue
            target = clauses_by_doc.get(other_doc.doc_id, {}).get(ref.target_section)
            if target is not None:
                return other_doc.doc_id, target
        # An explicit cross-document redirect was requested but that document
        # isn't in the analyzed set (or doesn't have the section) -- don't
        # silently fall back to a same-document match, that could point to
        # the wrong clause entirely.
        return None, None

    target = clauses_by_doc.get(doc.doc_id, {}).get(ref.target_section)
    if target is not None:
        return doc.doc_id, target
    return None, None


def _general_override_snippet(text: str) -> str:
    m = _GENERAL_OVERRIDE_SNIPPET_RE.search(text)
    return m.group(0).strip() if m else text[:150].strip()


def _cycle_edges(graph: nx.DiGraph, cycle_nodes: list[str]) -> list[GraphEdge]:
    edges = []
    n = len(cycle_nodes)
    for i in range(n):
        u, v = cycle_nodes[i], cycle_nodes[(i + 1) % n]
        data = graph.get_edge_data(u, v)
        edges.append(GraphEdge(source=u, target=v, kind=data["kind"], raw_text=data["raw_text"], context=data["context"]))
    return edges


def _find_circular_references(graph: nx.DiGraph) -> list[CircularReferenceGroup]:
    groups = []
    for cycle_nodes in nx.simple_cycles(graph):
        if len(cycle_nodes) < 2:
            continue  # self-loops are filtered out before edges are ever added, but guard anyway
        edges = _cycle_edges(graph, cycle_nodes)
        severity = "override_conflict" if all(e.kind == "notwithstanding_override" for e in edges) else "circular_reference"
        groups.append(CircularReferenceGroup(clause_ids=cycle_nodes, severity=severity, edges=edges))
    return groups


def build_dependency_graph(documents: list[ParsedDocument]) -> ClauseGraphResult:
    graph = nx.DiGraph()
    clauses_by_doc: dict[str, dict[str, Clause]] = {}
    docs_by_type: dict[DocType, list[ParsedDocument]] = defaultdict(list)

    for doc in documents:
        clauses_by_doc[doc.doc_id] = {c.section_number: c for c in doc.clauses if c.section_number}
        docs_by_type[doc.doc_type].append(doc)
        for c in doc.clauses:
            if not c.section_number:
                continue
            graph.add_node(
                c.id,
                doc_id=doc.doc_id,
                doc_type=doc.doc_type.value,
                section_number=c.section_number,
                heading=c.heading,
                has_general_override=c.has_general_override,
            )

    overrides: list[NotwithstandingOverride] = []
    unresolved: list[UnresolvedReference] = []
    general_overrides: list[GeneralOverride] = []

    for doc in documents:
        for clause in doc.clauses:
            if not clause.section_number:
                continue

            if clause.has_general_override:
                general_overrides.append(
                    GeneralOverride(clause_id=clause.id, snippet=_general_override_snippet(clause.text))
                )

            for ref in clause.references:
                if ref.type != ReferenceType.SECTION or not ref.target_section:
                    continue

                target_doc_id, target_clause = _resolve_section_reference(doc, clause, ref, clauses_by_doc, docs_by_type)
                if target_clause is None:
                    unresolved.append(
                        UnresolvedReference(
                            clause_id=clause.id,
                            raw_text=ref.raw_text,
                            target_section=ref.target_section,
                            context=ref.context,
                        )
                    )
                    continue

                target_id = f"{target_doc_id}::{ref.target_section}"
                if target_id == clause.id:
                    continue  # a clause referring to itself ("this Section 9.1") isn't a dependency edge

                kind = "notwithstanding_override" if ref.is_notwithstanding else "reference"
                graph.add_edge(clause.id, target_id, kind=kind, raw_text=ref.raw_text, context=ref.context)
                if ref.is_notwithstanding:
                    overrides.append(
                        NotwithstandingOverride(
                            overriding_clause_id=clause.id,
                            overridden_clause_id=target_id,
                            raw_text=ref.raw_text,
                        )
                    )

    circular_references = _find_circular_references(graph)

    nodes = [
        GraphNode(
            id=node_id,
            doc_id=data["doc_id"],
            doc_type=data["doc_type"],
            section_number=data["section_number"],
            heading=data["heading"],
            has_general_override=data["has_general_override"],
        )
        for node_id, data in graph.nodes(data=True)
    ]
    edges = [
        GraphEdge(source=u, target=v, kind=data["kind"], raw_text=data["raw_text"], context=data["context"])
        for u, v, data in graph.edges(data=True)
    ]

    analysis = GraphAnalysis(
        nodes=nodes,
        edges=edges,
        overrides=overrides,
        general_overrides=general_overrides,
        unresolved_references=unresolved,
        circular_references=circular_references,
    )
    return ClauseGraphResult(graph=graph, analysis=analysis)
