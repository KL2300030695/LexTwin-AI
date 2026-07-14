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
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {docLabel} &middot; Page{' '}
        {clause.page_start === clause.page_end ? clause.page_start : `${clause.page_start}-${clause.page_end}`}
      </p>
      {breadcrumb && breadcrumb.length > 0 ? (
        <p className="mt-1 text-xs text-slate-400">
          {breadcrumb.map((b, i) => (
            <span key={b.sectionNumber}>
              {i > 0 && <span className="mx-1">&rsaquo;</span>}
              {b.sectionNumber}
              {b.heading ? ` ${b.heading}` : ''}
            </span>
          ))}
        </p>
      ) : (
        <p className="mt-1 text-xs text-slate-400">Section {clause.section_number ?? '—'}</p>
      )}
      <h3 className="mt-1 text-base font-semibold text-slate-900">{clause.heading}</h3>
      <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{clause.text}</p>
    </div>
  )
}
