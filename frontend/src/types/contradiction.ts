export type ContradictionStatus = 'analyzed' | 'cannot_evaluate' | 'error'

export interface ContradictionResult {
  topic: string
  msa_clause_id: string
  sow_clause_id: string
  status: ContradictionStatus
  has_contradiction: boolean | null
  explanation: string | null
  confidence: number | null
  reason: string | null
}

export interface ContradictionAnalysis {
  msa_doc_id: string
  sow_doc_id: string
  results: ContradictionResult[]
  contradictions_found: number
}
