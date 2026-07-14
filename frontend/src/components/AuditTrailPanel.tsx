import type { AuditEntry } from '../types/audit'

const DECISION_STYLES: Record<AuditEntry['decision'], string> = {
  pending: 'bg-amber-100 text-amber-800',
  approved: 'bg-emerald-100 text-emerald-800',
  rejected: 'bg-red-100 text-red-800',
}

export default function AuditTrailPanel({
  entries,
  onDecide,
}: {
  entries: AuditEntry[]
  onDecide: (entryId: string, decision: 'approved' | 'rejected') => void
}) {
  if (entries.length === 0) {
    return <p className="text-sm text-slate-500">No audit trail entries yet. Log a redline suggestion to start one.</p>
  }

  return (
    <ul className="space-y-3">
      {entries.map((entry) => (
        <li key={entry.id} className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {entry.topic ?? entry.risk_rating} &middot; {entry.clause_id}
              </p>
              <p className="text-xs text-slate-400">Logged {new Date(entry.created_at).toLocaleString()}</p>
            </div>
            <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${DECISION_STYLES[entry.decision]}`}>
              {entry.decision}
            </span>
          </div>

          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <div>
              <p className="text-xs font-semibold text-slate-500">Original text</p>
              <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">{entry.original_text}</p>
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-500">AI suggestion</p>
              <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">{entry.ai_suggestion ?? '—'}</p>
            </div>
          </div>
          {entry.ai_rationale && <p className="mt-2 text-sm italic text-slate-500">{entry.ai_rationale}</p>}

          {entry.decision === 'pending' ? (
            <div className="mt-3 flex gap-2">
              <button
                onClick={() => onDecide(entry.id, 'approved')}
                className="rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-500"
              >
                Approve
              </button>
              <button
                onClick={() => onDecide(entry.id, 'rejected')}
                className="rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-500"
              >
                Reject
              </button>
            </div>
          ) : (
            <p className="mt-3 text-xs text-slate-400">
              {entry.decision === 'approved' ? 'Approved' : 'Rejected'} by {entry.reviewer ?? 'reviewer'}
              {entry.decided_at ? ` on ${new Date(entry.decided_at).toLocaleString()}` : ''}
            </p>
          )}
        </li>
      ))}
    </ul>
  )
}
