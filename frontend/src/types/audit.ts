export type AuditDecision = 'pending' | 'approved' | 'rejected'

export interface AuditEntry {
  id: string
  msa_doc_id: string
  sow_doc_id: string
  doc_id: string
  clause_id: string
  topic: string | null
  original_text: string
  risk_rating: string
  ai_suggestion: string | null
  ai_rationale: string | null
  decision: AuditDecision
  reviewer: string | null
  created_at: string
  decided_at: string | null
}

export interface AuditEntryCreate {
  msa_doc_id: string
  sow_doc_id: string
  doc_id: string
  clause_id: string
  topic?: string | null
  original_text: string
  risk_rating: string
  ai_suggestion?: string | null
  ai_rationale?: string | null
}
