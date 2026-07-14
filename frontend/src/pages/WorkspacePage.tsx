import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  analyzeContradictions,
  analyzeGraph,
  checkCompleteness,
  decideAuditEntry,
  extractObligations,
  getDocument,
  listAuditEntries,
} from '../api/client'
import type { Clause, ParsedDocument } from '../types/document'
import type { GraphAnalysis } from '../types/graph'
import type { CompletenessAnalysis } from '../types/completeness'
import type { ContradictionAnalysis } from '../types/contradiction'
import type { AuditEntry } from '../types/audit'
import type { Obligation } from '../types/obligation'
import { buildRiskFlags, type RiskFlag } from '../lib/riskFlags'
import RiskFlagsList from '../components/RiskFlagsList'
import RiskDetailPanel from '../components/RiskDetailPanel'
import DependencyGraph from '../components/DependencyGraph'
import ClauseCard from '../components/ClauseCard'
import AuditTrailPanel from '../components/AuditTrailPanel'
import ObligationsPanel from '../components/ObligationsPanel'

type Tab = 'risks' | 'graph' | 'obligations' | 'audit'

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

  if (!msaId || !sowId) return <p className="p-8 text-red-600">Missing document ids.</p>
  if (loading) return <p className="p-8 text-slate-500">Analyzing documents…</p>

  const selectedGraphClause = selectedClauseId ? clauseLookup.get(selectedClauseId) : null

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <Link to="/" className="text-sm text-slate-500 hover:underline">
        ← Back to documents
      </Link>
      <h1 className="mt-2 text-2xl font-bold text-slate-900">
        {msaDoc?.filename} <span className="text-slate-400">vs</span> {sowDoc?.filename}
      </h1>

      {contradictionError && (
        <div className="mt-3 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800">
          {contradictionError}
        </div>
      )}

      <div className="mt-6 flex gap-2 border-b border-slate-200">
        {(['risks', 'graph', 'obligations', 'audit'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium capitalize ${
              tab === t ? 'border-slate-900 text-slate-900' : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            {t === 'risks'
              ? `Risk Flags (${riskFlags.length})`
              : t === 'graph'
                ? 'Dependency Graph'
                : t === 'obligations'
                  ? `Obligations (${obligations.length})`
                  : `Audit Trail (${auditEntries.length})`}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {tab === 'risks' && (
          <div className="grid gap-6 md:grid-cols-[320px_1fr]">
            <RiskFlagsList flags={riskFlags} selectedId={selectedFlag?.id ?? null} onSelect={setSelectedFlag} />
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
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

        {tab === 'audit' && <AuditTrailPanel entries={auditEntries} onDecide={handleDecide} />}
      </div>
    </div>
  )
}
