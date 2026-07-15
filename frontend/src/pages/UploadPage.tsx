import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { analyzeGraph, listDocuments, uploadDocument } from '../api/client'
import type { DocType, ParsedDocument } from '../types/document'

const DOC_TYPE_STYLE: Record<DocType, { tint: string; text: string; border: string; label: string }> = {
  MSA: { tint: 'bg-seal-blue-tint', text: 'text-seal-blue', border: 'border-seal-blue/30', label: 'MSA' },
  SOW: { tint: 'bg-clay-tint', text: 'text-clay', border: 'border-clay/30', label: 'SOW' },
  OTHER: { tint: 'bg-ledger-soft', text: 'text-slate-body', border: 'border-ledger', label: 'DOC' },
}

function DocTypeTag({ docType }: { docType: DocType }) {
  const s = DOC_TYPE_STYLE[docType]
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-sm border px-2 py-0.5 font-mono text-[11px] font-semibold uppercase tracking-wider ${s.tint} ${s.text} ${s.border}`}
    >
      {s.label}
    </span>
  )
}

function MetaPill({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-sm border border-ledger bg-ledger-soft px-2 py-0.5 font-mono text-[11px] tabular-nums text-ink-soft">
      {children}
    </span>
  )
}

function UploadIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth="1.5" stroke="currentColor" className={className} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 16V4m0 0 4 4m-4-4-4 4" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v2.5A1.5 1.5 0 0 0 5.5 20h13a1.5 1.5 0 0 0 1.5-1.5V16" />
    </svg>
  )
}

function GovernsConnector() {
  return (
    <div
      className="flex shrink-0 flex-row items-center justify-center gap-1.5 py-1 sm:w-20 sm:flex-col sm:py-0"
      aria-hidden="true"
    >
      <svg width="56" height="14" viewBox="0 0 56 14" className="hidden text-slate-body/50 sm:block" fill="none">
        <line x1="0" y1="7" x2="46" y2="7" stroke="currentColor" strokeWidth="1.5" strokeDasharray="3 3" />
        <path d="M46 2.5 52 7 46 11.5" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <svg width="14" height="36" viewBox="0 0 14 36" className="text-slate-body/50 sm:hidden" fill="none">
        <line x1="7" y1="0" x2="7" y2="26" stroke="currentColor" strokeWidth="1.5" strokeDasharray="3 3" />
        <path d="M2.5 26 7 32 11.5 26" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <span className="font-mono text-[10px] font-medium uppercase tracking-widest text-slate-body">governs</span>
    </div>
  )
}

interface CircularWarning {
  count: number
  detail: string
}

function UploadSlot({
  docType,
  onUploaded,
}: {
  docType: DocType
  onUploaded: (d: ParsedDocument, circularCount: number) => void
}) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [circularWarning, setCircularWarning] = useState<CircularWarning | null>(null)

  async function handleFile(file: File) {
    setBusy(true)
    setError(null)
    setCircularWarning(null)
    try {
      const doc = await uploadDocument(file, docType)

      // Real-time drafting-loop check: a circular reference between two
      // clauses in the SAME document doesn't need a second document or a
      // workspace visit to be detectable -- it's caught the moment this one
      // document is parsed, surfaced right here rather than buried in a
      // later tab. (Cross-document cycles still need both MSA and SOW, and
      // are caught once a pair is analyzed in the workspace.)
      let circularCount = 0
      try {
        const graph = await analyzeGraph([doc.doc_id])
        circularCount = graph.circular_references.length
        if (circularCount > 0) {
          const first = graph.circular_references[0]
          const detail = first.edges
            .map((e) => `${e.source.split('::')[1] ?? e.source} ↔ ${e.target.split('::')[1] ?? e.target}`)
            .join(', ')
          setCircularWarning({ count: circularCount, detail })
        }
      } catch {
        // Best-effort -- if this check fails, full workspace analysis will
        // still catch it later; don't block the upload on it.
      }

      onUploaded(doc, circularCount)
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Upload failed'
      setError(msg)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex-1 rounded-md border border-ledger bg-white p-5 sm:p-6">
      <DocTypeTag docType={docType} />
      <div className="mt-5 flex flex-col items-center rounded-sm border border-dashed border-ledger px-4 py-8 text-center">
        <UploadIcon className="h-6 w-6 text-slate-body" />
        <label className="mt-4 inline-flex cursor-pointer items-center rounded-sm border border-ink bg-white px-4 py-2 text-sm font-medium text-ink transition-colors hover:bg-ledger-soft has-[:focus-visible]:outline-none has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-seal-blue has-[:focus-visible]:ring-offset-2 has-[:focus-visible]:ring-offset-paper">
          {busy ? 'Uploading…' : 'Choose PDF or DOCX'}
          <input
            type="file"
            accept=".pdf,.docx"
            className="sr-only"
            disabled={busy}
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) void handleFile(file)
              e.target.value = ''
            }}
          />
        </label>
        <p className="mt-3 font-mono text-[11px] uppercase tracking-wide text-slate-body">PDF &middot; DOCX</p>
      </div>
      {error && <p className="mt-3 text-sm text-redline">{error}</p>}
      {circularWarning && (
        <div className="mt-3 rounded-md border border-redline/30 bg-redline-tint px-3.5 py-3 text-sm text-redline">
          <p className="font-semibold">
            Circular reference detected — {circularWarning.count} loop{circularWarning.count === 1 ? '' : 's'} found
          </p>
          <p className="mt-1 font-mono text-xs">{circularWarning.detail}</p>
        </div>
      )}
    </div>
  )
}

function PairAnalysisPicker({ documents }: { documents: ParsedDocument[] }) {
  const navigate = useNavigate()
  const msaOptions = useMemo(() => documents.filter((d) => d.doc_type === 'MSA'), [documents])
  const sowOptions = useMemo(() => documents.filter((d) => d.doc_type === 'SOW'), [documents])

  const [msaId, setMsaId] = useState('')
  const [sowId, setSowId] = useState('')

  useEffect(() => {
    if (!msaId && msaOptions.length > 0) setMsaId(msaOptions[0].doc_id)
  }, [msaOptions, msaId])
  useEffect(() => {
    if (!sowId && sowOptions.length > 0) setSowId(sowOptions[0].doc_id)
  }, [sowOptions, sowId])

  if (msaOptions.length === 0 || sowOptions.length === 0) return null

  const selectClasses =
    'w-full rounded-sm border border-ledger bg-white px-3 py-2 text-sm text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-seal-blue focus-visible:ring-offset-2 focus-visible:ring-offset-paper sm:w-60'

  return (
    <section className="mt-10 rounded-md border border-ledger bg-white p-5 sm:p-6">
      <div className="flex items-baseline gap-2">
        <span className="font-mono text-xs font-semibold text-slate-body">&sect;2</span>
        <h2 className="font-serif text-lg font-medium text-ink">Analyze a document pair</h2>
      </div>
      <p className="mt-1.5 max-w-2xl text-sm text-slate-body">
        Pick the governing MSA and the SOW to check for dependency issues and cross-document contradictions.
      </p>
      <div className="mt-5 flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-end">
        <label className="text-sm">
          <span className="mb-1.5 block font-mono text-[11px] font-semibold uppercase tracking-wider text-slate-body">MSA</span>
          <select value={msaId} onChange={(e) => setMsaId(e.target.value)} className={selectClasses}>
            {msaOptions.map((d) => (
              <option key={d.doc_id} value={d.doc_id}>
                {d.filename}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1.5 block font-mono text-[11px] font-semibold uppercase tracking-wider text-slate-body">SOW</span>
          <select value={sowId} onChange={(e) => setSowId(e.target.value)} className={selectClasses}>
            {sowOptions.map((d) => (
              <option key={d.doc_id} value={d.doc_id}>
                {d.filename}
              </option>
            ))}
          </select>
        </label>
        <button
          onClick={() => navigate(`/workspace/${msaId}/${sowId}`)}
          disabled={!msaId || !sowId}
          className="w-full rounded-sm border border-ink bg-ink px-5 py-2.5 text-sm font-semibold tracking-wide text-paper transition-colors hover:bg-ink-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-seal-blue focus-visible:ring-offset-2 focus-visible:ring-offset-paper disabled:cursor-not-allowed disabled:border-ledger disabled:bg-ledger-soft disabled:text-slate-body sm:ml-auto sm:w-auto"
        >
          Start Analysis
        </button>
      </div>
    </section>
  )
}

export default function UploadPage() {
  const [documents, setDocuments] = useState<ParsedDocument[]>([])
  const [loading, setLoading] = useState(true)
  const [circularCounts, setCircularCounts] = useState<Map<string, number>>(new Map())

  useEffect(() => {
    listDocuments()
      .then(setDocuments)
      .finally(() => setLoading(false))
  }, [])

  function handleUploaded(doc: ParsedDocument, circularCount: number) {
    setDocuments((prev) => [doc, ...prev.filter((d) => d.doc_id !== doc.doc_id)])
    if (circularCount > 0) {
      setCircularCounts((prev) => new Map(prev).set(doc.doc_id, circularCount))
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 sm:py-10">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="flex items-center gap-1.5 font-mono text-xs font-semibold uppercase tracking-widest text-slate-body">
            <span aria-hidden="true">&#9878;</span> LexTwin AI
          </p>
          <h1 className="mt-1 font-serif text-2xl font-medium text-ink sm:text-3xl">Contract &amp; SOW Risk Analyzer</h1>
          <p className="mt-1.5 text-sm text-slate-body sm:text-base">Upload a governing MSA and a SOW to begin analysis.</p>
        </div>
        <Link
          to="/playbook"
          className="inline-flex shrink-0 items-center self-start rounded-sm border border-ledger px-3 py-1.5 text-sm font-medium text-ink transition-colors hover:border-ink hover:bg-ledger-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-seal-blue focus-visible:ring-offset-2 focus-visible:ring-offset-paper"
        >
          Manage Playbook
        </Link>
      </div>

      <section className="mt-8">
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-xs font-semibold text-slate-body">&sect;1</span>
          <h2 className="font-serif text-lg font-medium text-ink">Document intake</h2>
        </div>
        <div className="mt-4 flex flex-col items-stretch gap-2 sm:flex-row sm:items-center sm:gap-0">
          <UploadSlot docType="MSA" onUploaded={handleUploaded} />
          <GovernsConnector />
          <UploadSlot docType="SOW" onUploaded={handleUploaded} />
        </div>
      </section>

      <PairAnalysisPicker documents={documents} />

      <section className="mt-10">
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-xs font-semibold text-slate-body">&sect;3</span>
          <h2 className="font-serif text-lg font-medium text-ink">
            Uploaded documents <span className="font-mono text-base font-normal text-slate-body">&middot; {documents.length}</span>
          </h2>
        </div>

        {loading && <p className="mt-4 text-sm text-slate-body">Loading&hellip;</p>}
        {!loading && documents.length === 0 && (
          <p className="mt-4 rounded-md border border-dashed border-ledger bg-white px-5 py-6 text-center text-sm text-slate-body">
            No documents uploaded yet.
          </p>
        )}
        {documents.length > 0 && (
          <ul className="mt-4 divide-y divide-ledger overflow-hidden rounded-md border border-ledger bg-white">
            {documents.map((doc) => (
              <li key={doc.doc_id} className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-start gap-3">
                  <DocTypeTag docType={doc.doc_type} />
                  <div>
                    <Link
                      to={`/document/${doc.doc_id}`}
                      className="rounded-sm text-sm font-semibold text-ink hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-seal-blue focus-visible:ring-offset-2"
                    >
                      {doc.filename}
                    </Link>
                    <div className="mt-1.5 flex flex-wrap gap-1.5">
                      <MetaPill>{doc.clauses.length} clauses</MetaPill>
                      <MetaPill>{doc.tables.length} tables</MetaPill>
                      <MetaPill>{doc.page_count} pages</MetaPill>
                      {circularCounts.has(doc.doc_id) && (
                        <span className="inline-flex items-center rounded-sm border border-redline/30 bg-redline-tint px-2 py-0.5 font-mono text-[11px] font-semibold text-redline">
                          &#9888; circular reference
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <Link
                  to={`/document/${doc.doc_id}`}
                  className="inline-flex shrink-0 items-center self-start rounded-sm border border-ledger px-3 py-1.5 text-sm font-medium text-ink transition-colors hover:border-ink hover:bg-ledger-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-seal-blue focus-visible:ring-offset-2 sm:self-auto"
                >
                  View
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
