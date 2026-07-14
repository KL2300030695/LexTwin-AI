import type { AuditEntry } from '../types/audit'

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

export default function AuditTrailPanel({
  entries,
  onDecide,
}: {
  entries: AuditEntry[]
  onDecide: (entryId: string, decision: 'approved' | 'rejected') => void
}) {
  if (entries.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-ledger bg-white p-5 text-sm text-slate-body">
        No audit trail entries yet. Log a redline suggestion to start one.
      </div>
    )
  }

  return (
    <ul className="space-y-3">
      {entries.map((entry) => (
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

          {entry.decision === 'pending' ? (
            <div className="mt-3.5 flex gap-2">
              <button
                onClick={() => onDecide(entry.id, 'approved')}
                className="rounded-sm border border-ink bg-ink px-3.5 py-1.5 text-sm font-semibold text-paper transition-colors hover:bg-ink-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-seal-blue focus-visible:ring-offset-2"
              >
                Approve
              </button>
              <button
                onClick={() => onDecide(entry.id, 'rejected')}
                className="rounded-sm border border-ledger px-3.5 py-1.5 text-sm font-medium text-ink transition-colors hover:border-ink hover:bg-ledger-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-seal-blue focus-visible:ring-offset-2"
              >
                Reject
              </button>
            </div>
          ) : (
            <p className="mt-3.5 font-mono text-[11px] text-slate-body">
              {entry.decision === 'approved' ? 'Approved' : 'Rejected'} by {entry.reviewer ?? 'reviewer'}
              {entry.decided_at ? ` on ${new Date(entry.decided_at).toLocaleString()}` : ''}
            </p>
          )}
        </li>
      ))}
    </ul>
  )
}
