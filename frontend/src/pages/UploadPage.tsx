import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listDocuments, uploadDocument } from '../api/client'
import type { DocType, ParsedDocument } from '../types/document'

function UploadSlot({ docType, onUploaded }: { docType: DocType; onUploaded: (d: ParsedDocument) => void }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleFile(file: File) {
    setBusy(true)
    setError(null)
    try {
      const doc = await uploadDocument(file, docType)
      onUploaded(doc)
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Upload failed'
      setError(msg)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex-1 rounded-lg border-2 border-dashed border-slate-300 bg-white p-6 text-center">
      <p className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">{docType}</p>
      <label className="inline-block cursor-pointer rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700">
        {busy ? 'Uploading…' : 'Choose PDF or DOCX'}
        <input
          type="file"
          accept=".pdf,.docx"
          className="hidden"
          disabled={busy}
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) void handleFile(file)
            e.target.value = ''
          }}
        />
      </label>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
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

  return (
    <div className="mt-8 rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="text-sm font-semibold text-slate-900">Analyze a document pair</h2>
      <p className="mt-1 text-sm text-slate-500">
        Pick the governing MSA and the SOW to check for dependency issues and cross-document contradictions.
      </p>
      <div className="mt-3 flex flex-wrap items-end gap-3">
        <label className="text-sm">
          <span className="mb-1 block font-medium text-slate-700">MSA</span>
          <select
            value={msaId}
            onChange={(e) => setMsaId(e.target.value)}
            className="rounded-md border border-slate-300 px-2 py-1.5"
          >
            {msaOptions.map((d) => (
              <option key={d.doc_id} value={d.doc_id}>
                {d.filename}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1 block font-medium text-slate-700">SOW</span>
          <select
            value={sowId}
            onChange={(e) => setSowId(e.target.value)}
            className="rounded-md border border-slate-300 px-2 py-1.5"
          >
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
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
        >
          Start Analysis
        </button>
      </div>
    </div>
  )
}

export default function UploadPage() {
  const [documents, setDocuments] = useState<ParsedDocument[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    listDocuments()
      .then(setDocuments)
      .finally(() => setLoading(false))
  }, [])

  function handleUploaded(doc: ParsedDocument) {
    setDocuments((prev) => [doc, ...prev.filter((d) => d.doc_id !== doc.doc_id)])
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Contract &amp; SOW Risk Analyzer</h1>
          <p className="mt-1 text-slate-600">Upload a governing MSA and a SOW to begin analysis.</p>
        </div>
        <Link to="/playbook" className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100">
          Manage Playbook
        </Link>
      </div>

      <div className="mt-8 flex gap-4">
        <UploadSlot docType="MSA" onUploaded={handleUploaded} />
        <UploadSlot docType="SOW" onUploaded={handleUploaded} />
      </div>

      <PairAnalysisPicker documents={documents} />

      <h2 className="mt-10 mb-3 text-lg font-semibold text-slate-900">Uploaded documents</h2>
      {loading && <p className="text-slate-500">Loading…</p>}
      {!loading && documents.length === 0 && <p className="text-slate-500">No documents uploaded yet.</p>}
      <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
        {documents.map((doc) => (
          <li key={doc.doc_id} className="flex items-center justify-between px-4 py-3">
            <div>
              <Link to={`/document/${doc.doc_id}`} className="font-medium text-slate-900 hover:underline">
                {doc.filename}
              </Link>
              <p className="text-sm text-slate-500">
                {doc.doc_type} · {doc.clauses.length} clauses · {doc.tables.length} tables · {doc.page_count} pages
              </p>
            </div>
            <Link
              to={`/document/${doc.doc_id}`}
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              View
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}
