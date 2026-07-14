import { useState } from 'react'
import type { Clause } from '../types/document'
import type { RiskFlag } from '../lib/riskFlags'
import { SEVERITY_STYLE } from '../lib/riskFlags'
import type { RedlineSuggestion } from '../types/redline'
import { createAuditEntry, generateRedline } from '../api/client'
import ClauseCard from './ClauseCard'
import DiffView from './DiffView'

interface ClauseLookupEntry {
  clause: Clause
  docLabel: string
  siblingClauses: Clause[]
}

function ConfidenceMeter({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  return (
    <div className="flex items-center gap-2.5">
      <div className="h-1.5 w-24 overflow-hidden rounded-full bg-white" role="presentation">
        <div className="h-full rounded-full bg-redline" style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono text-xs font-semibold tabular-nums text-redline">{pct}% confidence</span>
    </div>
  )
}

export default function RiskDetailPanel({
  flag,
  clauseLookup,
  msaDocId,
  sowDocId,
  onLogged,
}: {
  flag: RiskFlag | null
  clauseLookup: Map<string, ClauseLookupEntry>
  msaDocId: string
  sowDocId: string
  onLogged?: () => void
}) {
  const [redline, setRedline] = useState<RedlineSuggestion | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [logged, setLogged] = useState(false)

  if (!flag) {
    return (
      <div className="flex min-h-[220px] items-center justify-center rounded-md border border-dashed border-ledger text-sm text-slate-body">
        Select a flagged risk to see details.
      </div>
    )
  }

  const clauses = flag.clauseIds.map((id) => clauseLookup.get(id)).filter((c): c is ClauseLookupEntry => !!c)
  const isContradiction = flag.kind === 'contradiction' && flag.contradiction

  async function handleGenerateRedline() {
    if (!flag?.contradiction) return
    setLoading(true)
    setError(null)
    try {
      const suggestion = await generateRedline({
        docId: sowDocId,
        clauseId: flag.contradiction.sow_clause_id,
        riskReason: flag.contradiction.explanation ?? flag.title,
        referenceDocId: msaDocId,
        referenceClauseId: flag.contradiction.msa_clause_id,
      })
      setRedline(suggestion)
      setLogged(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to generate redline suggestion.')
    } finally {
      setLoading(false)
    }
  }

  async function handleLogToAuditTrail() {
    if (!flag?.contradiction || !redline) return
    await createAuditEntry({
      msa_doc_id: msaDocId,
      sow_doc_id: sowDocId,
      doc_id: sowDocId,
      clause_id: flag.contradiction.sow_clause_id,
      topic: flag.contradiction.topic,
      original_text: redline.original_text,
      risk_rating: 'contradiction',
      ai_suggestion: redline.suggested_text,
      ai_rationale: redline.rationale,
    })
    setLogged(true)
    onLogged?.()
  }

  return (
    <div className="space-y-4">
      <div>
        <p className={`font-mono text-[11px] font-semibold uppercase tracking-wider ${SEVERITY_STYLE[flag.severity].text}`}>
          {flag.severity} severity
        </p>
        <h2 className="mt-1 font-serif text-lg font-medium text-ink">{flag.title}</h2>
        {flag.description && <p className="mt-1.5 text-sm text-slate-body">{flag.description}</p>}
      </div>

      {isContradiction && flag.contradiction?.confidence != null && (
        <div className="rounded-md border border-redline/30 bg-redline-tint px-3.5 py-3">
          <ConfidenceMeter value={flag.contradiction.confidence} />
        </div>
      )}

      <div className="grid gap-3 md:grid-cols-2">
        {clauses.map(({ clause, docLabel, siblingClauses }) => (
          <ClauseCard key={clause.id} clause={clause} docLabel={docLabel} siblingClauses={siblingClauses} />
        ))}
      </div>

      {isContradiction && (
        <div className="rounded-md border border-ledger bg-white p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="font-serif text-base font-medium text-ink">Suggested fallback language</h3>
            <button
              onClick={handleGenerateRedline}
              disabled={loading}
              className="shrink-0 rounded-sm border border-ink bg-ink px-3.5 py-1.5 text-sm font-semibold text-paper transition-colors hover:bg-ink-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-seal-blue focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:border-ledger disabled:bg-ledger-soft disabled:text-slate-body"
            >
              {loading ? 'Generating…' : redline ? 'Regenerate' : 'Generate Redline'}
            </button>
          </div>

          {error && <p className="mt-2 text-sm text-redline">{error}</p>}

          {redline && (
            <div className="mt-3.5 space-y-3.5">
              <div className="rounded-sm border border-ledger bg-ledger-soft/60 p-3.5">
                <DiffView diff={redline.diff} />
              </div>
              <p className="text-sm text-slate-body">
                <span className="font-semibold text-ink">Rationale — </span>
                {redline.rationale}
              </p>
              <button
                onClick={handleLogToAuditTrail}
                disabled={logged}
                className="rounded-sm border border-ledger px-3.5 py-1.5 text-sm font-medium text-ink transition-colors hover:border-ink hover:bg-ledger-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-seal-blue focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {logged ? 'Logged to audit trail ✓' : 'Log to Audit Trail'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
