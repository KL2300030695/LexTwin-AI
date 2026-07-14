import { useMemo, useState } from 'react'
import type { Clause } from '../types/document'
import type { Obligation } from '../types/obligation'
import ClauseCard from './ClauseCard'

type ClauseLookupEntry = { clause: Clause; docLabel: string; siblingClauses: Clause[] }

function DeadlineBadge({ obligation }: { obligation: Obligation }) {
  if (obligation.deadline_days === null) {
    return <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">No stated deadline</span>
  }
  return (
    <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">
      {obligation.deadline_days} day{obligation.deadline_days === 1 ? '' : 's'}
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
      <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
        No obligations (shall/must/will/agrees-to language) were detected in these documents.
      </div>
    )
  }

  return (
    <div className="grid gap-6 md:grid-cols-[1fr_360px]">
      <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
        {obligations.map((o) => {
          const entry = clauseLookup.get(o.clause_id)
          return (
            <li key={o.id}>
              <button
                onClick={() => setSelectedId(o.id)}
                className={`block w-full px-4 py-3 text-left text-sm hover:bg-slate-50 ${
                  o.id === selectedId ? 'bg-slate-50 ring-1 ring-inset ring-slate-300' : ''
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {entry?.docLabel ?? o.doc_id} &middot; Section {o.section_number ?? '—'}
                  </p>
                  <DeadlineBadge obligation={o} />
                </div>
                <p className="mt-1 font-medium text-slate-900">
                  {o.responsible_party ?? 'Unspecified party'}{' '}
                  <span className="font-normal text-slate-500">{o.obligation_verb}</span>
                </p>
                <p className="mt-1 line-clamp-2 text-slate-600">{o.text}</p>
              </button>
            </li>
          )
        })}
      </ul>

      <div>
        {selected && selectedClauseEntry ? (
          <div className="space-y-3">
            <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Obligation</p>
              <p className="mt-1">
                <span className="font-medium text-slate-900">{selected.responsible_party ?? 'Unspecified party'}</span>{' '}
                <span className="text-slate-500">{selected.obligation_verb}</span>
              </p>
              {selected.deadline_text && <p className="mt-1 text-slate-600">Deadline: {selected.deadline_text}</p>}
            </div>
            <ClauseCard
              clause={selectedClauseEntry.clause}
              docLabel={selectedClauseEntry.docLabel}
              siblingClauses={selectedClauseEntry.siblingClauses}
            />
          </div>
        ) : (
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
            Select an obligation to see its source clause.
          </div>
        )}
      </div>
    </div>
  )
}
