import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  analyzeContradictions,
  analyzeGraph,
  checkCompleteness,
  decideAuditEntry,
  extractObligations,
  generateReport,
  getDocument,
  listAuditEntries,
} from '../api/client'
import type { Clause, ParsedDocument } from '../types/document'
import type { GraphAnalysis } from '../types/graph'
import type { CompletenessAnalysis } from '../types/completeness'
import type { ContradictionAnalysis } from '../types/contradiction'
import type { AuditEntry } from '../types/audit'
import type { Obligation } from '../types/obligation'
import type { ReportRequest } from '../types/report'
import { buildRiskFlags, type RiskFlag } from '../lib/riskFlags'
import RiskFlagsList from '../components/RiskFlagsList'
import RiskDetailPanel from '../components/RiskDetailPanel'
import DependencyGraph from '../components/DependencyGraph'
import ClauseCard from '../components/ClauseCard'
import AuditTrailPanel from '../components/AuditTrailPanel'
import ObligationsPanel from '../components/ObligationsPanel'
import ChatPanel from '../components/ChatPanel'

type Tab = 'risks' | 'graph' | 'obligations' | 'chat' | 'audit'

export default function WorkspacePage() {
  const { msaId, sowId } = useParams<{ msaId: string; sowId: string }>()

  const [msaDoc, setMsaDoc] = useState<ParsedDocument | null>(null)
  const [sowDoc, setSowDoc] = useState<ParsedDocument | null>(null)
  const [graph, setGraph] = useState<GraphAnalysis | null>(null)
  const [completeness, setCompleteness] = useState<CompletenessAnalysis | null>(null)
  const [contradictions, setContradictions] = useState<ContradictionAnalysis | null>(null)
  const [obligations, setObligations] = useState<Obligation[]>([])
  const [auditEntries, setAuditEntries] = useState<AuditEntry[]>([])

  const [loading, setLoading] = useState(true)
  const [contradictionError, setContradictionError] = useState<string | null>(null)
  const [reportError, setReportError] = useState<string | null>(null)
  const [downloadingReport, setDownloadingReport] = useState(false)

  const [tab, setTab] = useState<Tab>('risks')
  const [selectedFlag, setSelectedFlag] = useState<RiskFlag | null>(null)
  const [selectedClauseId, setSelectedClauseId] = useState<string | null>(null)

  const refreshAudit = useCallback(() => {
    if (!msaId || !sowId) return
    listAuditEntries(msaId, sowId).then(setAuditEntries)
  }, [msaId, sowId])

  useEffect(() => {
    if (!msaId || !sowId) return
    let cancelled = false

    async function load() {
      setLoading(true)
      const [msa, sow] = await Promise.all([getDocument(msaId!), getDocument(sowId!)])
      if (cancelled) return
      setMsaDoc(msa)
      setSowDoc(sow)

      const [graphResult, completenessResult, obligationsResult] = await Promise.all([
        analyzeGraph([msaId!, sowId!]),
        checkCompleteness([msaId!, sowId!]),
        extractObligations([msaId!, sowId!]),
      ])
      if (cancelled) return
      setGraph(graphResult)
      setCompleteness(completenessResult)
      setObligations(obligationsResult)

      try {
        const contradictionResult = await analyzeContradictions(msaId!, sowId!)
        if (!cancelled) {
          setContradictions(contradictionResult)
          // A failed Claude call comes back as a 200 with per-pair status:
          // "error" (so one bad pair doesn't kill the whole analysis) --
          // surface it, or a user with no API key configured would see
          // "2 risks" with no indication that AI checks silently skipped.
          const erroredTopics = contradictionResult.results.filter((r) => r.status === 'error')
          if (erroredTopics.length > 0) {
            setContradictionError(
              `AI contradiction detection failed for ${erroredTopics.length} topic(s) (${erroredTopics
                .map((r) => r.topic)
                .join(', ')}): ${erroredTopics[0].reason}`,
            )
          }
        }
      } catch (e) {
        if (!cancelled) {
          setContradictionError(
            e instanceof Error
              ? `AI contradiction detection unavailable: ${e.message}`
              : 'AI contradiction detection unavailable.',
          )
        }
      }

      if (!cancelled) {
        await listAuditEntries(msaId!, sowId!).then(setAuditEntries)
        setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [msaId, sowId])

  const clauseLookup = useMemo(() => {
    const map = new Map<string, { clause: Clause; docLabel: string; siblingClauses: Clause[] }>()
    for (const c of msaDoc?.clauses ?? [])
      map.set(c.id, { clause: c, docLabel: `MSA (${msaDoc!.filename})`, siblingClauses: msaDoc!.clauses })
    for (const c of sowDoc?.clauses ?? [])
      map.set(c.id, { clause: c, docLabel: `SOW (${sowDoc!.filename})`, siblingClauses: sowDoc!.clauses })
    return map
  }, [msaDoc, sowDoc])

  const riskFlags = useMemo(() => buildRiskFlags(graph, completeness, contradictions), [graph, completeness, contradictions])

  async function handleDecide(entryId: string, decision: 'approved' | 'rejected') {
    await decideAuditEntry(entryId, decision)
    refreshAudit()
  }

  async function handleDownloadReport() {
    if (!msaDoc || !sowDoc) return
    setDownloadingReport(true)
    setReportError(null)
    try {
      const payload: ReportRequest = {
        msa_filename: msaDoc.filename,
        sow_filename: sowDoc.filename,
        risk_flags: riskFlags.map((f) => ({
          id: f.id,
          kind: f.kind,
          severity: f.severity,
          title: f.title,
          description: f.description,
          clause_ids: f.clauseIds,
          confidence: f.contradiction?.confidence ?? null,
        })),
        obligations,
        audit_entries: auditEntries,
      }
      const blob = await generateReport(payload)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${msaDoc.filename}_vs_${sowDoc.filename}_risk_report.pdf`
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
    } catch (e) {
      setReportError(e instanceof Error ? e.message : 'Failed to generate report.')
    } finally {
      setDownloadingReport(false)
    }
  }

  if (!msaId || !sowId) return <p className="p-8 text-sm text-redline">Missing document ids.</p>
  if (loading) return <p className="p-8 text-sm text-slate-body">Analyzing documents&hellip;</p>

  const selectedGraphClause = selectedClauseId ? clauseLookup.get(selectedClauseId) : null

  const TAB_META: Record<Tab, { label: string; count: number | null }> = {
    risks: { label: 'Risk Flags', count: riskFlags.length },
    graph: { label: 'Dependency Graph', count: null },
    obligations: { label: 'Obligations', count: obligations.length },
    chat: { label: 'Chat', count: null },
    audit: { label: 'Audit Trail', count: auditEntries.length },
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <Link
            to="/"
            className="inline-flex items-center gap-1 rounded-sm font-mono text-xs text-slate-body transition-colors hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-seal-blue focus-visible:ring-offset-2"
          >
            &larr; back to documents
          </Link>
          <h1 className="mt-2 font-serif text-2xl font-medium text-ink sm:text-3xl">
            {msaDoc?.filename} <span className="px-1 text-base font-normal text-slate-body">vs</span> {sowDoc?.filename}
          </h1>
        </div>
        <button
          onClick={handleDownloadReport}
          disabled={downloadingReport}
          className="inline-flex shrink-0 items-center gap-1.5 self-start rounded-sm border border-ledger px-3.5 py-2 text-sm font-medium text-ink transition-colors hover:border-ink hover:bg-ledger-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-seal-blue focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 sm:mt-0"
        >
          {downloadingReport ? 'Preparing report…' : 'Download Report'}
        </button>
      </div>

      {contradictionError && (
        <div className="mt-3 rounded-md border border-seal-amber/30 bg-seal-amber-tint px-3.5 py-3 text-sm text-seal-amber">
          {contradictionError}
        </div>
      )}

      {reportError && (
        <div className="mt-3 rounded-md border border-redline/30 bg-redline-tint px-3.5 py-3 text-sm text-redline">
          {reportError}
        </div>
      )}

      <div className="mt-6 flex gap-1 overflow-x-auto border-b border-ledger">
        {(['risks', 'graph', 'obligations', 'chat', 'audit'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`-mb-px flex shrink-0 items-center gap-1.5 border-b-2 px-3.5 py-2.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-seal-blue focus-visible:ring-offset-2 ${
              tab === t ? 'border-ink text-ink' : 'border-transparent text-slate-body hover:text-ink'
            }`}
          >
            {TAB_META[t].label}
            {TAB_META[t].count !== null && (
              <span className="rounded-sm bg-ledger-soft px-1.5 py-0.5 font-mono text-[11px] tabular-nums text-ink-soft">
                {TAB_META[t].count}
              </span>
            )}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {tab === 'risks' && (
          <div className="grid gap-5 md:grid-cols-[320px_1fr]">
            <RiskFlagsList flags={riskFlags} selectedId={selectedFlag?.id ?? null} onSelect={setSelectedFlag} />
            <div className="rounded-md border border-ledger bg-white p-4 sm:p-5">
              <RiskDetailPanel
                flag={selectedFlag}
                clauseLookup={clauseLookup}
                msaDocId={msaId}
                sowDocId={sowId}
                onLogged={refreshAudit}
              />
            </div>
          </div>
        )}

        {tab === 'graph' && graph && (
          <div className="space-y-4">
            <DependencyGraph graph={graph} msaDocId={msaId} sowDocId={sowId} onSelectClause={setSelectedClauseId} />
            {selectedGraphClause && (
              <ClauseCard
                clause={selectedGraphClause.clause}
                docLabel={selectedGraphClause.docLabel}
                siblingClauses={selectedGraphClause.siblingClauses}
              />
            )}
          </div>
        )}

        {tab === 'obligations' && <ObligationsPanel obligations={obligations} clauseLookup={clauseLookup} />}

        {tab === 'chat' && <ChatPanel docIds={[msaId, sowId]} clauseLookup={clauseLookup} />}

        {tab === 'audit' && <AuditTrailPanel entries={auditEntries} onDecide={handleDecide} />}
      </div>
    </div>
  )
}
