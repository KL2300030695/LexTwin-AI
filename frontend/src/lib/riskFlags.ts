import type { GraphAnalysis } from '../types/graph'
import type { CompletenessAnalysis } from '../types/completeness'
import type { ContradictionAnalysis, ContradictionResult } from '../types/contradiction'

export type RiskFlagKind =
  | 'contradiction'
  | 'override_conflict'
  | 'circular_reference'
  | 'missing_reference'
  | 'broken_reference'
  | 'blanket_override'

export type RiskSeverity = 'high' | 'medium' | 'low'

export interface RiskFlag {
  id: string
  kind: RiskFlagKind
  severity: RiskSeverity
  title: string
  description: string
  clauseIds: string[]
  contradiction?: ContradictionResult
}

const KIND_LABEL: Record<RiskFlagKind, string> = {
  contradiction: 'Contradiction',
  override_conflict: 'Circular Override Conflict',
  circular_reference: 'Circular Reference',
  missing_reference: 'Missing Reference',
  broken_reference: 'Broken Reference',
  blanket_override: 'Blanket Override',
}

export function riskFlagLabel(kind: RiskFlagKind): string {
  return KIND_LABEL[kind]
}

export function buildRiskFlags(
  graph: GraphAnalysis | null,
  completeness: CompletenessAnalysis | null,
  contradictions: ContradictionAnalysis | null,
): RiskFlag[] {
  const flags: RiskFlag[] = []

  if (contradictions) {
    for (const r of contradictions.results) {
      if (r.status === 'analyzed' && r.has_contradiction) {
        flags.push({
          id: `contradiction-${r.msa_clause_id}-${r.sow_clause_id}`,
          kind: 'contradiction',
          severity: 'high',
          title: `${r.topic}: MSA and SOW conflict`,
          description: r.explanation ?? '',
          clauseIds: [r.msa_clause_id, r.sow_clause_id],
          contradiction: r,
        })
      }
    }
  }

  if (graph) {
    for (const group of graph.circular_references) {
      const isConflict = group.severity === 'override_conflict'
      flags.push({
        id: `circular-${group.clause_ids.join('-')}`,
        kind: isConflict ? 'override_conflict' : 'circular_reference',
        severity: isConflict ? 'high' : 'medium',
        title: isConflict
          ? 'Circular override conflict -- precedence cannot be resolved'
          : 'Circular reference between clauses',
        description: group.edges.map((e) => `${e.source} references ${e.target} ("${e.raw_text}")`).join('; '),
        clauseIds: group.clause_ids,
      })
    }

    for (const gen of graph.general_overrides) {
      flags.push({
        id: `blanket-override-${gen.clause_id}`,
        kind: 'blanket_override',
        severity: 'medium',
        title: 'Blanket "Notwithstanding" override with no specific target',
        description: gen.snippet,
        clauseIds: [gen.clause_id],
      })
    }

    for (const u of graph.unresolved_references) {
      flags.push({
        id: `broken-ref-${u.clause_id}-${u.target_section}`,
        kind: 'broken_reference',
        severity: 'low',
        title: `References Section ${u.target_section}, which could not be resolved`,
        description: u.context,
        clauseIds: [u.clause_id],
      })
    }
  }

  if (completeness) {
    for (const status of completeness.clause_statuses) {
      if (!status.can_evaluate) {
        flags.push({
          id: `missing-ref-${status.clause_id}`,
          kind: 'missing_reference',
          severity: 'medium',
          title: status.reason ?? 'Cannot evaluate -- missing reference',
          description: status.missing_references.map((m) => m.label).join(', '),
          clauseIds: [status.clause_id],
        })
      }
    }
  }

  const severityRank: Record<RiskSeverity, number> = { high: 0, medium: 1, low: 2 }
  return flags.sort((a, b) => severityRank[a.severity] - severityRank[b.severity])
}
