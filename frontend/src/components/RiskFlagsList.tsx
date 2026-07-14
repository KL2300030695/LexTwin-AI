import type { RiskFlag } from '../lib/riskFlags'
import { riskFlagLabel } from '../lib/riskFlags'

const SEVERITY_STYLES: Record<RiskFlag['severity'], string> = {
  high: 'border-red-300 bg-red-50 text-red-800',
  medium: 'border-amber-300 bg-amber-50 text-amber-800',
  low: 'border-slate-300 bg-slate-50 text-slate-700',
}

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
      <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
        No risks flagged for this document pair.
      </div>
    )
  }

  return (
    <ul className="space-y-2">
      {flags.map((flag) => (
        <li key={flag.id}>
          <button
            onClick={() => onSelect(flag)}
            className={`w-full rounded-lg border p-3 text-left text-sm transition ${
              flag.id === selectedId ? 'ring-2 ring-slate-900' : ''
            } ${SEVERITY_STYLES[flag.severity]}`}
          >
            <p className="text-xs font-semibold uppercase tracking-wide opacity-80">
              {riskFlagLabel(flag.kind)} &middot; {flag.severity}
            </p>
            <p className="mt-1 font-medium">{flag.title}</p>
          </button>
        </li>
      ))}
    </ul>
  )
}
