import type { DiffOp } from '../types/redline'

export default function DiffView({ diff }: { diff: DiffOp[] }) {
  return (
    <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink">
      {diff.map((op, i) => {
        if (op.type === 'equal') return <span key={i}>{op.text}</span>
        if (op.type === 'delete')
          return (
            <span key={i} className="rounded-sm bg-redline-tint text-redline line-through decoration-redline/70">
              {op.text}
            </span>
          )
        return (
          <span key={i} className="rounded-sm bg-ledger-soft font-medium text-ink underline decoration-ink/40 underline-offset-2">
            {op.text}
          </span>
        )
      })}
    </p>
  )
}
