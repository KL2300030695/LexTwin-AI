import type { Clause } from '../types/document'
import { buildBreadcrumb } from '../lib/breadcrumb'

export default function ClauseCard({
  clause,
  docLabel,
  siblingClauses,
}: {
  clause: Clause
  docLabel: string
  /** All clauses from the same document, used to render the section-hierarchy
   * breadcrumb (e.g. "4 Service Levels › 4.2 Service Level Credits"). Omit to
   * fall back to showing just the leaf section number. */
  siblingClauses?: Clause[]
}) {
  const breadcrumb = siblingClauses ? buildBreadcrumb(clause, siblingClauses) : null

  return (
    <div className="rounded-md border border-ledger bg-white p-4">
      <p className="font-mono text-[11px] font-semibold uppercase tracking-wider text-slate-body">
        {docLabel} &middot; Page{' '}
        {clause.page_start === clause.page_end ? clause.page_start : `${clause.page_start}-${clause.page_end}`}
      </p>
      {breadcrumb && breadcrumb.length > 0 ? (
        <p className="mt-1.5 text-xs text-slate-body">
          {breadcrumb.map((b, i) => (
            <span key={b.sectionNumber}>
              {i > 0 && <span className="mx-1 text-ledger">&rsaquo;</span>}
              {b.sectionNumber}
              {b.heading ? ` ${b.heading}` : ''}
            </span>
          ))}
        </p>
      ) : (
        <p className="mt-1.5 text-xs text-slate-body">Section {clause.section_number ?? '—'}</p>
      )}
      <h3 className="mt-1.5 font-serif text-base font-medium text-ink">{clause.heading}</h3>
      <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-ink-soft">{clause.text}</p>
    </div>
  )
}
