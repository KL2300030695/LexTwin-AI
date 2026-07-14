export interface MissingReference {
  label: string
  type: string
  raw_text: string
  context: string
}

export interface ClauseEvaluationStatus {
  clause_id: string
  doc_id: string
  section_number: string
  can_evaluate: boolean
  missing_references: MissingReference[]
  reason: string | null
}

export interface CompletenessAnalysis {
  analyzed_doc_ids: string[]
  available_doc_types: string[]
  available_exhibit_labels: string[]
  clause_statuses: ClauseEvaluationStatus[]
  blocked_clause_count: number
  total_clause_count: number
}
