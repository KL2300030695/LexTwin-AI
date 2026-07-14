export type EdgeKind = 'reference' | 'notwithstanding_override'
export type CircularSeverity = 'override_conflict' | 'circular_reference'

export interface GraphNode {
  id: string
  doc_id: string
  doc_type: string
  section_number: string
  heading: string | null
  has_general_override: boolean
}

export interface GraphEdge {
  source: string
  target: string
  kind: EdgeKind
  raw_text: string
  context: string
}

export interface NotwithstandingOverride {
  overriding_clause_id: string
  overridden_clause_id: string
  raw_text: string
}

export interface GeneralOverride {
  clause_id: string
  snippet: string
}

export interface UnresolvedReference {
  clause_id: string
  raw_text: string
  target_section: string
  context: string
}

export interface CircularReferenceGroup {
  clause_ids: string[]
  severity: CircularSeverity
  edges: GraphEdge[]
}

export interface GraphAnalysis {
  nodes: GraphNode[]
  edges: GraphEdge[]
  overrides: NotwithstandingOverride[]
  general_overrides: GeneralOverride[]
  unresolved_references: UnresolvedReference[]
  circular_references: CircularReferenceGroup[]
}
