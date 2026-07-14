import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getDocument } from '../api/client'
import type { Clause, ParsedDocument } from '../types/document'

function referenceLabel(ref: Clause['references'][number]): string {
  const target = ref.target_section ?? ref.target_label ?? ref.raw_text
  return ref.is_notwithstanding ? `⚡ overrides ${target}` : target
}

export default function DocumentView() {
  const { docId } = useParams<{ docId: string }>()
  const [doc, setDoc] = useState<ParsedDocument | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!docId) return
    getDocument(docId)
      .then((d) => {
        setDoc(d)
        setSelectedId(d.clauses[0]?.id ?? null)
      })
      .catch(() => setError('Document not found'))
  }, [docId])

  if (error) return <p className="p-8 text-red-600">{error}</p>
  if (!doc) return <p className="p-8 text-slate-500">Loading…</p>

  const selected = doc.clauses.find((c) => c.id === selectedId) ?? null
  const missingExhibits = doc.known_exhibit_labels.filter((l) => !doc.available_exhibit_labels.includes(l))

  return (
    <div className="mx-auto flex max-w-6xl gap-6 px-6 py-8">
      <aside className="w-80 shrink-0">
        <Link to="/" className="text-sm text-slate-500 hover:underline">
          ← Back to documents
        </Link>
        <h1 className="mt-2 text-lg font-bold text-slate-900">{doc.filename}</h1>
        <p className="text-sm text-slate-500">
          {doc.doc_type} · {doc.clauses.length} clauses · {doc.page_count} pages
        </p>

        {missingExhibits.length > 0 && (
          <div className="mt-4 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800">
            <p className="font-semibold">Missing referenced documents</p>
            <ul className="mt-1 list-disc pl-4">
              {missingExhibits.map((label) => (
                <li key={label}>{label}</li>
              ))}
            </ul>
          </div>
        )}

        <nav className="mt-4 max-h-[70vh] overflow-y-auto rounded-lg border border-slate-200 bg-white">
          {doc.clauses.map((c) => (
            <button
              key={c.id}
              onClick={() => setSelectedId(c.id)}
              className={`block w-full truncate px-3 py-1.5 text-left text-sm hover:bg-slate-100 ${
                c.id === selectedId ? 'bg-slate-900 text-white hover:bg-slate-900' : 'text-slate-700'
              }`}
              style={{ paddingLeft: `${0.75 + Math.max(c.level - 1, 0) * 0.9}rem` }}
            >
              {c.section_number ? `${c.section_number} ` : ''}
              {c.heading ?? '(untitled)'}
            </button>
          ))}
        </nav>
      </aside>

      <main className="flex-1">
        {!selected && <p className="text-slate-500">Select a clause.</p>}
        {selected && (
          <div className="rounded-lg border border-slate-200 bg-white p-6">
            <p className="text-sm text-slate-500">
              Section {selected.section_number ?? '—'} · Page{' '}
              {selected.page_start === selected.page_end
                ? selected.page_start
                : `${selected.page_start}-${selected.page_end}`}
            </p>
            <h2 className="mt-1 text-xl font-semibold text-slate-900">{selected.heading}</h2>

            <pre className="mt-4 whitespace-pre-wrap font-sans text-sm leading-relaxed text-slate-800">
              {selected.text || '(no body text — heading only)'}
            </pre>

            {selected.references.length > 0 && (
              <div className="mt-6">
                <h3 className="text-sm font-semibold text-slate-900">References</h3>
                <ul className="mt-2 flex flex-wrap gap-2">
                  {selected.references.map((r, i) => (
                    <li
                      key={i}
                      className={`rounded-full border px-3 py-1 text-xs ${
                        r.is_notwithstanding
                          ? 'border-amber-400 bg-amber-50 text-amber-800'
                          : 'border-slate-300 bg-slate-50 text-slate-700'
                      }`}
                      title={r.context}
                    >
                      {referenceLabel(r)}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {selected.table_ids.length > 0 && (
              <div className="mt-6 space-y-4">
                <h3 className="text-sm font-semibold text-slate-900">Tables</h3>
                {selected.table_ids.map((tid) => {
                  const table = doc.tables.find((t) => t.id === tid)
                  if (!table) return null
                  return (
                    <div key={tid} className="overflow-x-auto rounded-md border border-slate-200">
                      <table className="w-full text-sm">
                        <tbody>
                          {table.rows.map((row, ri) => (
                            <tr key={ri} className={ri === 0 ? 'bg-slate-100 font-medium' : 'odd:bg-white even:bg-slate-50'}>
                              {row.map((cell, ci) => (
                                <td key={ci} className="border border-slate-200 px-3 py-1.5">
                                  {cell}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
