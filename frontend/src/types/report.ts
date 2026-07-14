import type { AuditEntry } from './audit'
import type { Obligation } from './obligation'

export interface ReportRiskFlag {
  id: string
  kind: string
  severity: string
  title: string
  description: string
  clause_ids: string[]
  confidence: number | null
}

export interface ReportRequest {
  msa_filename: string
  sow_filename: string
  risk_flags: ReportRiskFlag[]
  obligations: Obligation[]
  audit_entries: AuditEntry[]
}
