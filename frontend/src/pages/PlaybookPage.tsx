import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  getPlaybookReferenceCategories,
  getPlaybookTopics,
  resetPlaybookTopics,
  savePlaybookTopics,
} from '../api/client'
import type { ReferenceCategory, TopicRule } from '../types/playbook'

interface EditableTopic {
  topic: string
  patternsText: string
}

function toEditable(topics: TopicRule[]): EditableTopic[] {
  return topics.map((t) => ({ topic: t.topic, patternsText: t.patterns.join(', ') }))
}

function toTopicRules(editable: EditableTopic[]): TopicRule[] {
  return editable
    .filter((t) => t.topic.trim())
    .map((t) => ({
      topic: t.topic.trim(),
      patterns: t.patternsText
        .split(',')
        .map((p) => p.trim())
        .filter(Boolean),
    }))
}

export default function PlaybookPage() {
  const [topics, setTopics] = useState<EditableTopic[]>([])
  const [referenceCategories, setReferenceCategories] = useState<ReferenceCategory[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [openSources, setOpenSources] = useState<Set<string>>(new Set())

  useEffect(() => {
    getPlaybookTopics()
      .then((t) => setTopics(toEditable(t)))
      .finally(() => setLoading(false))
    getPlaybookReferenceCategories().then(setReferenceCategories)
  }, [])

  async function handleSave() {
    setSaving(true)
    setMessage(null)
    try {
      const saved = await savePlaybookTopics(toTopicRules(topics))
      setTopics(toEditable(saved))
      setMessage('Saved. New analyses will use this configuration.')
    } finally {
      setSaving(false)
    }
  }

  async function handleReset() {
    setSaving(true)
    setMessage(null)
    try {
      const defaults = await resetPlaybookTopics()
      setTopics(toEditable(defaults))
      setMessage('Reset to defaults.')
    } finally {
      setSaving(false)
    }
  }

  function updateTopic(index: number, field: keyof EditableTopic, value: string) {
    setTopics((prev) => prev.map((t, i) => (i === index ? { ...t, [field]: value } : t)))
  }

  function removeTopic(index: number) {
    setTopics((prev) => prev.filter((_, i) => i !== index))
  }

  function addTopic() {
    setTopics((prev) => [...prev, { topic: '', patternsText: '' }])
  }

  function toggleSource(source: string) {
    setOpenSources((prev) => {
      const next = new Set(prev)
      if (next.has(source)) next.delete(source)
      else next.add(source)
      return next
    })
  }

  if (loading) return <p className="p-8 text-slate-500">Loading playbook…</p>

  const categoriesBySource = new Map<string, ReferenceCategory[]>()
  for (const c of referenceCategories) {
    const list = categoriesBySource.get(c.source) ?? []
    list.push(c)
    categoriesBySource.set(c.source, list)
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <Link to="/" className="text-sm text-slate-500 hover:underline">
        ← Back to documents
      </Link>
      <h1 className="mt-2 text-2xl font-bold text-slate-900">Legal Playbook</h1>
      <p className="mt-1 text-slate-600">
        Topics used to align MSA and SOW clauses for contradiction detection. Each topic is matched against a
        clause's heading using case-insensitive regex patterns (comma-separated).
      </p>

      {message && <div className="mt-4 rounded-md border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-800">{message}</div>}

      <div className="mt-6 space-y-3">
        {topics.map((t, i) => (
          <div key={i} className="flex items-start gap-2 rounded-lg border border-slate-200 bg-white p-3">
            <div className="flex-1 space-y-2">
              <input
                value={t.topic}
                onChange={(e) => updateTopic(i, 'topic', e.target.value)}
                placeholder="Topic name (e.g. Payment Terms)"
                className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm font-medium"
              />
              <input
                value={t.patternsText}
                onChange={(e) => updateTopic(i, 'patternsText', e.target.value)}
                placeholder={'Regex patterns, comma-separated (e.g. \\binvoic, \\bpayment terms\\b)'}
                className="w-full rounded-md border border-slate-300 px-2 py-1.5 font-mono text-xs"
              />
            </div>
            <button
              onClick={() => removeTopic(i)}
              className="rounded-md border border-red-300 px-2 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50"
            >
              Remove
            </button>
          </div>
        ))}
      </div>

      <div className="mt-4 flex gap-2">
        <button
          onClick={addTopic}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100"
        >
          + Add topic
        </button>
        <button
          onClick={handleSave}
          disabled={saving}
          className="rounded-md bg-slate-900 px-4 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
        >
          Save
        </button>
        <button
          onClick={handleReset}
          disabled={saving}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-50"
        >
          Reset to defaults
        </button>
      </div>

      <div className="mt-8 border-t border-slate-200 pt-4">
        <p className="text-sm font-semibold text-slate-900">Reference categories</p>
        <p className="mt-1 text-sm text-slate-500">
          Real-world clause taxonomies pulled from public legal NLP datasets -- browse for inspiration when adding
          topics above, or as example language for redline suggestions.
        </p>

        <div className="mt-3 space-y-2">
          {[...categoriesBySource.entries()].map(([source, categories]) => (
            <div key={source} className="rounded-lg border border-slate-200">
              <button
                onClick={() => toggleSource(source)}
                className="flex w-full items-center justify-between px-3 py-2 text-left text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                <span>
                  {openSources.has(source) ? '▾' : '▸'} {source}
                </span>
                <span className="text-xs font-normal text-slate-400">{categories.length} categories</span>
              </button>
              {openSources.has(source) && (
                <ul className="grid gap-2 border-t border-slate-200 p-3 sm:grid-cols-2">
                  {categories.map((c) => (
                    <li key={`${c.source}::${c.category}`} className="rounded-md border border-slate-200 bg-slate-50 p-2 text-xs">
                      <p className="font-semibold text-slate-700">{c.category}</p>
                      {c.hypothesis && <p className="mt-1 italic text-slate-500">{c.hypothesis}</p>}
                      {c.example_clauses[0] && <p className="mt-1 line-clamp-2 text-slate-500">{c.example_clauses[0]}</p>}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
