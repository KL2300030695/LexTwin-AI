import axios from 'axios'
import type { DocType, ParsedDocument } from '../types/document'
import type { GraphAnalysis } from '../types/graph'
import type { CompletenessAnalysis } from '../types/completeness'
import type { ContradictionAnalysis } from '../types/contradiction'
import type { RedlineSuggestion } from '../types/redline'
import type { AuditDecision, AuditEntry, AuditEntryCreate } from '../types/audit'
import type { ReferenceCategory, TopicRule } from '../types/playbook'
import type { Obligation } from '../types/obligation'
import type { ReportRequest } from '../types/report'
import type { ChatRequest, ChatResponse } from '../types/chat'

const api = axios.create({ baseURL: '/api' })

export async function uploadDocument(file: File, docType: DocType): Promise<ParsedDocument> {
  const form = new FormData()
  form.append('file', file)
  form.append('doc_type', docType)
  const { data } = await api.post<ParsedDocument>('/documents/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function getDocument(docId: string): Promise<ParsedDocument> {
  const { data } = await api.get<ParsedDocument>(`/documents/${docId}`)
  return data
}

export async function listDocuments(): Promise<ParsedDocument[]> {
  const { data } = await api.get<ParsedDocument[]>('/documents')
  return data
}

export async function analyzeGraph(docIds: string[]): Promise<GraphAnalysis> {
  const { data } = await api.post<GraphAnalysis>('/graph/analyze', { doc_ids: docIds })
  return data
}

export async function checkCompleteness(docIds: string[]): Promise<CompletenessAnalysis> {
  const { data } = await api.post<CompletenessAnalysis>('/completeness/check', { doc_ids: docIds })
  return data
}

export async function analyzeContradictions(msaDocId: string, sowDocId: string): Promise<ContradictionAnalysis> {
  const { data } = await api.post<ContradictionAnalysis>('/contradictions/analyze', {
    msa_doc_id: msaDocId,
    sow_doc_id: sowDocId,
  })
  return data
}

export interface RedlineGenerateParams {
  docId: string
  clauseId: string
  riskReason: string
  referenceDocId?: string
  referenceClauseId?: string
}

export async function generateRedline(params: RedlineGenerateParams): Promise<RedlineSuggestion> {
  const { data } = await api.post<RedlineSuggestion>('/redline/generate', {
    doc_id: params.docId,
    clause_id: params.clauseId,
    risk_reason: params.riskReason,
    reference_doc_id: params.referenceDocId,
    reference_clause_id: params.referenceClauseId,
  })
  return data
}

export async function listAuditEntries(msaDocId: string, sowDocId: string): Promise<AuditEntry[]> {
  const { data } = await api.get<AuditEntry[]>('/audit/entries', {
    params: { msa_doc_id: msaDocId, sow_doc_id: sowDocId },
  })
  return data
}

export async function createAuditEntry(payload: AuditEntryCreate): Promise<AuditEntry> {
  const { data } = await api.post<AuditEntry>('/audit/entries', payload)
  return data
}

export async function decideAuditEntry(
  entryId: string,
  decision: AuditDecision,
  reviewer?: string,
): Promise<AuditEntry> {
  const { data } = await api.post<AuditEntry>(`/audit/entries/${entryId}/decision`, { decision, reviewer })
  return data
}

export async function getPlaybookTopics(): Promise<TopicRule[]> {
  const { data } = await api.get<TopicRule[]>('/playbook/topics')
  return data
}

export async function savePlaybookTopics(topics: TopicRule[]): Promise<TopicRule[]> {
  const { data } = await api.put<TopicRule[]>('/playbook/topics', { topics })
  return data
}

export async function resetPlaybookTopics(): Promise<TopicRule[]> {
  const { data } = await api.post<TopicRule[]>('/playbook/topics/reset')
  return data
}

export async function getPlaybookReferenceCategories(): Promise<ReferenceCategory[]> {
  const { data } = await api.get<ReferenceCategory[]>('/playbook/categories')
  return data
}

export async function extractObligations(docIds: string[]): Promise<Obligation[]> {
  const { data } = await api.post<Obligation[]>('/obligations/extract', { doc_ids: docIds })
  return data
}

export async function generateReport(payload: ReportRequest): Promise<Blob> {
  const { data } = await api.post<Blob>('/report/generate', payload, { responseType: 'blob' })
  return data
}

export async function askChat(payload: ChatRequest): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>('/chat/ask', payload)
  return data
}
