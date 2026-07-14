import { useMemo, useState } from 'react'
import type { Clause } from '../types/document'
import type { Obligation } from '../types/obligation'
import ClauseCard from './ClauseCard'

type ClauseLookupEntry = { clause: Clause; docLabel: string; siblingClauses: Clause[] }

function DeadlineBadge({ obligation }: { obligation: Obligation }) {
  if (obligation.deadline_days === null) {
    return (
      <span className="inline-flex shrink-0 items-center rounded-sm border border-ledger px-2 py-0.5 font-mono text-[11px] text-slate-body">
        no stated deadline
      </span>
    )
  }
  return (
    <span className="inline-flex shrink-0 items-center rounded-sm border border-ledger bg-ledger-soft px-2 py-0.5 font-mono text-[11px] font-semibold tabular-nums text-ink">
      {obligation.deadline_days}d
    </span>
  )
}

export default function ObligationsPanel({
  obligations,
  clauseLookup,
}: {
  obligations: Obligation[]
  clauseLookup: Map<string, ClauseLookupEntry>
}) {
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const selected = useMemo(() => obligations.find((o) => o.id === selectedId) ?? null, [obligations, selectedId])
  const selectedClauseEntry = selected ? clauseLookup.get(selected.clause_id) : null

  if (obligations.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-ledger bg-white p-5 text-sm text-slate-body">
        No obligations (shall/must/will/agrees-to language) were detected in these documents.
      </div>
    )
  }

  return (
    <div className="grid gap-6 md:grid-cols-[1fr_360px]">
      <ul className="divide-y divide-ledger overflow-hidden rounded-md border border-ledger bg-white">
        {obligations.map((o) => {
          const entry = clauseLookup.get(o.clause_id)
          return (
            <li key={o.id}>
              <button
                onClick={() => setSelectedId(o.id)}
                className={`block w-full px-4 py-3.5 text-left text-sm transition-colors hover:bg-ledger-soft/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-seal-blue ${
                  o.id === selectedId ? 'bg-ledger-soft/60 ring-1 ring-inset ring-ink' : ''
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <p className="font-mono text-[11px] font-semibold uppercase tracking-wider text-slate-body">
                    {entry?.docLabel ?? o.doc_id} &middot; Section {o.section_number ?? '—'}
                  </p>
                  <DeadlineBadge obligation={o} />
                </div>
                <p className="mt-1.5 font-medium text-ink">
                  {o.responsible_party ?? 'Unspecified party'}{' '}
                  <span className="font-normal text-slate-body">{o.obligation_verb}</span>
                </p>
                <p className="mt-1 line-clamp-2 text-ink-soft">{o.text}</p>
              </button>
            </li>
          )
        })}
      </ul>

      <div>
        {selected && selectedClauseEntry ? (
          <div className="space-y-3">
            <div className="rounded-md border border-ledger bg-white p-4 text-sm">
              <p className="font-mono text-[11px] font-semibold uppercase tracking-wider text-slate-body">Obligation</p>
              <p className="mt-1.5">
                <span className="font-medium text-ink">{selected.responsible_party ?? 'Unspecified party'}</span>{' '}
                <span className="text-slate-body">{selected.obligation_verb}</span>
              </p>
              {selected.deadline_text && <p className="mt-1 text-slate-body">Deadline: {selected.deadline_text}</p>}
            </div>
            <ClauseCard
              clause={selectedClauseEntry.clause}
              docLabel={selectedClauseEntry.docLabel}
              siblingClauses={selectedClauseEntry.siblingClauses}
            />
          </div>
        ) : (
          <div className="flex min-h-[160px] items-center justify-center rounded-md border border-dashed border-ledger text-sm text-slate-body">
            Select an obligation to see its source clause.
          </div>
        )}
      </div>
    </div>
  )
}
