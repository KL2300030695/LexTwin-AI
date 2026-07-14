import type { RiskFlag } from '../lib/riskFlags'
import { riskFlagLabel, SEVERITY_STYLE } from '../lib/riskFlags'

export default function RiskFlagsList({
  flags,
  selectedId,
  onSelect,
}: {
  flags: RiskFlag[]
  selectedId: string | null
  onSelect: (flag: RiskFlag) => void
}) {
  if (flags.length === 0) {
    return (
      <div className="rounded-md border border-ledger bg-white p-5 text-sm">
        <p className="font-medium text-ink">No risks flagged for this document pair.</p>
        <p className="mt-1 text-slate-body">All dependency, completeness, and contradiction checks passed.</p>
      </div>
    )
  }

  return (
    <ul className="space-y-2">
      {flags.map((flag) => {
        const s = SEVERITY_STYLE[flag.severity]
        return (
          <li key={flag.id}>
            <button
              onClick={() => onSelect(flag)}
              className={`w-full rounded-md border p-3.5 text-left text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-seal-blue focus-visible:ring-offset-2 ${s.tint} ${s.border} ${
                flag.id === selectedId ? 'ring-2 ring-ink ring-offset-2' : ''
              }`}
            >
              <p className={`flex items-center gap-1.5 font-mono text-[11px] font-semibold uppercase tracking-wider ${s.text}`}>
                <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${s.dot}`} aria-hidden="true" />
                {riskFlagLabel(flag.kind)} &middot; {flag.severity}
              </p>
              <p className="mt-1.5 font-medium text-ink">{flag.title}</p>
            </button>
          </li>
        )
      })}
    </ul>
  )
}
