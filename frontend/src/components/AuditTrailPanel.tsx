import { useState } from 'react'
import type { AuditEntry } from '../types/audit'
import { useAuth } from '../contexts/AuthContext'
import { hasRoleAtLeast } from '../types/user'

const DECISION_PILL: Record<AuditEntry['decision'], string> = {
  pending: 'border-seal-amber/30 bg-seal-amber-tint text-seal-amber',
  approved: 'border-ledger bg-ledger-soft text-ink',
  rejected: 'border-ledger bg-ledger-soft text-ink',
}

const DECISION_LABEL: Record<AuditEntry['decision'], string> = {
  pending: 'Pending review',
  approved: 'Approved ✓',
  rejected: 'Rejected',
}

function formatDecisionLine(decision: AuditEntry['decision'], reviewer: string | null, decidedAt: string | null): string {
  const who = reviewer ?? 'reviewer'
  const when = decidedAt ? ` on ${new Date(decidedAt).toLocaleString()}` : ''
  return `${decision === 'approved' ? 'Approved' : 'Rejected'} by ${who}${when}`
}

export default function AuditTrailPanel({
  entries,
  onDecide,
}: {
  entries: AuditEntry[]
  onDecide: (entryId: string, decision: 'approved' | 'rejected') => void
}) {
  const [editingId, setEditingId] = useState<string | null>(null)
  const [historyOpenId, setHistoryOpenId] = useState<string | null>(null)
  const { profile } = useAuth()
  // Recording a decision requires 'approver' or higher on the backend (see
  // app/routers/audit.py) -- hiding the controls for a plain reviewer here
  // avoids showing a button that would just 403, but the backend is what
  // actually enforces this; this is a UX convenience, not the security boundary.
  const canDecide = hasRoleAtLeast(profile?.role, 'approver')

  if (entries.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-ledger bg-white p-5 text-sm text-slate-body">
        No audit trail entries yet. Log a redline suggestion to start one.
      </div>
    )
  }

  return (
    <ul className="space-y-3">
      {entries.map((entry) => {
        const isEditing = canDecide && (entry.decision === 'pending' || editingId === entry.id)
        const hasHistory = entry.revision_history.length > 0
        const isHistoryOpen = historyOpenId === entry.id

        return (
          <li key={entry.id} className="rounded-md border border-ledger bg-white p-4 sm:p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="font-mono text-[11px] font-semibold uppercase tracking-wider text-slate-body">
                  {entry.topic ?? entry.risk_rating} &middot; {entry.clause_id}
                </p>
                <p className="mt-0.5 font-mono text-[11px] text-slate-body/70">
                  Logged {new Date(entry.created_at).toLocaleString()}
                </p>
              </div>
              <span
                className={`inline-flex shrink-0 items-center rounded-sm border px-2 py-0.5 font-mono text-[11px] font-semibold uppercase tracking-wider ${DECISION_PILL[entry.decision]}`}
              >
                {DECISION_LABEL[entry.decision]}
              </span>
            </div>

            <div className="mt-3.5 grid gap-3.5 sm:grid-cols-2">
              <div>
                <p className="font-mono text-[11px] font-semibold uppercase tracking-wider text-slate-body">Original text</p>
                <p className="mt-1 whitespace-pre-wrap text-sm text-ink-soft">{entry.original_text}</p>
              </div>
              <div>
                <p className="font-mono text-[11px] font-semibold uppercase tracking-wider text-slate-body">AI suggestion</p>
                <p className="mt-1 whitespace-pre-wrap text-sm text-ink-soft">{entry.ai_suggestion ?? '—'}</p>
              </div>
            </div>
            {entry.ai_rationale && <p className="mt-2.5 text-sm italic text-slate-body">{entry.ai_rationale}</p>}

            {isEditing ? (
              <div className="mt-3.5 flex flex-wrap items-center gap-2">
                <button
                  onClick={() => {
                    onDecide(entry.id, 'approved')
                    setEditingId(null)
                  }}
                  className="rounded-sm border border-ink bg-ink px-3.5 py-1.5 text-sm font-semibold text-paper transition-colors hover:bg-ink-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-seal-blue focus-visible:ring-offset-2"
                >
                  Approve
                </button>
                <button
                  onClick={() => {
                    onDecide(entry.id, 'rejected')
                    setEditingId(null)
                  }}
                  className="rounded-sm border border-ledger px-3.5 py-1.5 text-sm font-medium text-ink transition-colors hover:border-ink hover:bg-ledger-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-seal-blue focus-visible:ring-offset-2"
                >
                  Reject
                </button>
                {entry.decision !== 'pending' && (
                  <button
                    onClick={() => setEditingId(null)}
                    className="rounded-sm px-2 py-1.5 font-mono text-[11px] text-slate-body underline decoration-slate-body/40 underline-offset-2 transition-colors hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-seal-blue"
                  >
                    Cancel
                  </button>
                )}
              </div>
            ) : (
              <div className="mt-3.5 flex flex-wrap items-center justify-between gap-2">
                <p className="font-mono text-[11px] text-slate-body">
                  {entry.decision === 'pending'
                    ? 'Pending review — needs an approver to decide'
                    : formatDecisionLine(entry.decision, entry.reviewer, entry.decided_at)}
                  {hasHistory && ` · corrected ${entry.revision_history.length}×`}
                </p>
                <div className="flex items-center gap-3">
                  {hasHistory && (
                    <button
                      onClick={() => setHistoryOpenId(isHistoryOpen ? null : entry.id)}
                      className="font-mono text-[11px] text-slate-body underline decoration-slate-body/40 underline-offset-2 transition-colors hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-seal-blue"
                    >
                      {isHistoryOpen ? 'Hide history' : 'View history'}
                    </button>
                  )}
                  {canDecide && entry.decision !== 'pending' && (
                    <button
                      onClick={() => setEditingId(entry.id)}
                      className="rounded-sm border border-ledger px-2.5 py-1 font-mono text-[11px] text-slate-body transition-colors hover:border-ink hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-seal-blue"
                    >
                      Change decision
                    </button>
                  )}
                </div>
              </div>
            )}

            {isHistoryOpen && hasHistory && (
              <ul className="mt-2.5 space-y-1 rounded-sm border border-ledger bg-ledger-soft/50 p-3">
                {entry.revision_history.map((rev, i) => (
                  <li key={i} className="font-mono text-[11px] text-slate-body">
                    {formatDecisionLine(rev.decision, rev.reviewer, rev.decided_at)}{' '}
                    <span className="text-slate-body/70">(superseded)</span>
                  </li>
                ))}
              </ul>
            )}
          </li>
        )
      })}
    </ul>
  )
}
