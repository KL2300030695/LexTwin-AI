import type { DiffOp } from '../types/redline'

export default function DiffView({ diff }: { diff: DiffOp[] }) {
  return (
    <p className="whitespace-pre-wrap text-sm leading-relaxed">
      {diff.map((op, i) => {
        if (op.type === 'equal') return <span key={i}>{op.text}</span>
        if (op.type === 'delete')
          return (
            <span key={i} className="bg-red-100 text-red-700 line-through decoration-red-500">
              {op.text}
            </span>
          )
        return (
          <span key={i} className="bg-emerald-100 font-medium text-emerald-800 underline decoration-emerald-500">
            {op.text}
          </span>
        )
      })}
    </p>
  )
}
