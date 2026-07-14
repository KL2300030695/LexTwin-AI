import { useState } from 'react'
import type { KeyboardEvent } from 'react'
import type { Clause } from '../types/document'
import type { ChatCitation, ChatMessage } from '../types/chat'
import { askChat } from '../api/client'
import ClauseCard from './ClauseCard'

type ClauseLookupEntry = { clause: Clause; docLabel: string; siblingClauses: Clause[] }

interface DisplayMessage extends ChatMessage {
  citations?: ChatCitation[]
}

export default function ChatPanel({
  docIds,
  clauseLookup,
}: {
  docIds: string[]
  clauseLookup: Map<string, ClauseLookupEntry>
}) {
  const [messages, setMessages] = useState<DisplayMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedCitationClauseId, setSelectedCitationClauseId] = useState<string | null>(null)

  async function handleSend() {
    const question = input.trim()
    if (!question || loading) return
    setInput('')
    setError(null)
    const history = messages.map(({ role, content }) => ({ role, content }))
    setMessages((prev) => [...prev, { role: 'user', content: question }])
    setLoading(true)
    try {
      const response = await askChat({ doc_ids: docIds, question, history })
      setMessages((prev) => [...prev, { role: 'assistant', content: response.answer, citations: response.citations }])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to get an answer.')
      setMessages((prev) => prev.slice(0, -1))
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void handleSend()
    }
  }

  const selectedClauseEntry = selectedCitationClauseId ? clauseLookup.get(selectedCitationClauseId) : null

  return (
    <div className="grid gap-5 md:grid-cols-[1fr_360px]">
      <div className="flex h-[65vh] flex-col rounded-md border border-ledger bg-white">
        <div className="flex-1 space-y-4 overflow-y-auto p-4 sm:p-5">
          {messages.length === 0 && (
            <div className="flex h-full items-center justify-center px-6 text-center text-sm text-slate-body">
              Ask a question about this MSA/SOW pair &mdash; e.g. &ldquo;What are the payment terms?&rdquo; or &ldquo;Is
              there a conflict in the service levels?&rdquo;
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[85%] rounded-md px-3.5 py-2.5 text-sm ${
                  m.role === 'user' ? 'bg-ink text-paper' : 'border border-ledger bg-white text-ink'
                }`}
              >
                <p className="whitespace-pre-wrap leading-relaxed">{m.content}</p>
                {m.citations && m.citations.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5 border-t border-ledger/60 pt-2">
                    {m.citations.map((c) => (
                      <button
                        key={c.clause_id}
                        onClick={() => setSelectedCitationClauseId(c.clause_id)}
                        className={`rounded-sm border px-1.5 py-0.5 font-mono text-[11px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-seal-blue ${
                          selectedCitationClauseId === c.clause_id
                            ? 'border-seal-blue bg-seal-blue-tint text-seal-blue'
                            : 'border-ledger text-slate-body hover:border-ink hover:text-ink'
                        }`}
                      >
                        {clauseLookup.get(c.clause_id)?.docLabel.split(' ')[0] ?? c.doc_id} &sect;{c.section_number ?? '?'}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="rounded-md border border-ledger bg-white px-3.5 py-2.5 text-sm text-slate-body">
                Thinking&hellip;
              </div>
            </div>
          )}
        </div>

        {error && <div className="border-t border-redline/30 bg-redline-tint px-4 py-2.5 text-sm text-redline">{error}</div>}

        <div className="flex items-end gap-2 border-t border-ledger p-3">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about this MSA/SOW pair…"
            rows={1}
            className="flex-1 resize-none rounded-sm border border-ledger px-3 py-2 text-sm text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-seal-blue focus-visible:ring-offset-2"
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="shrink-0 rounded-sm border border-ink bg-ink px-4 py-2 text-sm font-semibold text-paper transition-colors hover:bg-ink-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-seal-blue focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:border-ledger disabled:bg-ledger-soft disabled:text-slate-body"
          >
            Send
          </button>
        </div>
      </div>

      <div>
        {selectedClauseEntry ? (
          <ClauseCard
            clause={selectedClauseEntry.clause}
            docLabel={selectedClauseEntry.docLabel}
            siblingClauses={selectedClauseEntry.siblingClauses}
          />
        ) : (
          <div className="flex min-h-[160px] items-center justify-center rounded-md border border-dashed border-ledger text-sm text-slate-body">
            Click a citation to see its source clause.
          </div>
        )}
      </div>
    </div>
  )
}
