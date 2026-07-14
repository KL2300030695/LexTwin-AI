import { useState } from 'react'
import type { Clause } from '../types/document'
import type { RiskFlag } from '../lib/riskFlags'
import type { RedlineSuggestion } from '../types/redline'
import { createAuditEntry, generateRedline } from '../api/client'
import ClauseCard from './ClauseCard'
import DiffView from './DiffView'

interface ClauseLookupEntry {
  clause: Clause
  docLabel: string
  siblingClauses: Clause[]
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
    return <p className="text-sm text-slate-500">Select a flagged risk to see details.</p>
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
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{flag.severity} severity</p>
        <h2 className="text-lg font-semibold text-slate-900">{flag.title}</h2>
        {flag.description && <p className="mt-1 text-sm text-slate-600">{flag.description}</p>}
      </div>

      {isContradiction && flag.contradiction && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          <p className="font-semibold">
            Confidence: {flag.contradiction.confidence != null ? `${Math.round(flag.contradiction.confidence * 100)}%` : '—'}
          </p>
        </div>
      )}

      <div className="grid gap-3 md:grid-cols-2">
        {clauses.map(({ clause, docLabel, siblingClauses }) => (
          <ClauseCard key={clause.id} clause={clause} docLabel={docLabel} siblingClauses={siblingClauses} />
        ))}
      </div>

      {isContradiction && (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-900">Suggested fallback language</h3>
            <button
              onClick={handleGenerateRedline}
              disabled={loading}
              className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
            >
              {loading ? 'Generating…' : redline ? 'Regenerate' : 'Generate Redline'}
            </button>
          </div>

          {error && <p className="mt-2 text-sm text-red-600">{error}</p>}

          {redline && (
            <div className="mt-3 space-y-3">
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                <DiffView diff={redline.diff} />
              </div>
              <p className="text-sm text-slate-600">
                <span className="font-semibold text-slate-800">Rationale: </span>
                {redline.rationale}
              </p>
              <button
                onClick={handleLogToAuditTrail}
                disabled={logged}
                className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-50"
              >
                {logged ? 'Logged to audit trail' : 'Log to Audit Trail'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
