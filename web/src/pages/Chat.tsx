import { KeyboardEvent, useEffect, useRef, useState } from 'react'
import Sidebar from '../components/Sidebar'
import MessageBubble from '../components/MessageBubble'
import api from '../api/client'
import { AlertItem, DataSummary } from '../types'
import { buildSuggestions } from '../lib/suggestions'
import { useChat } from '../lib/useChat'

export default function Chat() {
  const { messages, streaming, send, clearHistory } = useChat()
  const [input, setInput]     = useState('')
  const [atRisk, setAtRisk]   = useState<AlertItem[]>([])
  const [summary, setSummary] = useState<DataSummary | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api.get('/data/summary').then((r) => setSummary(r.data)).catch(() => {})
    api.get('/data/alerts').then((r) => setAtRisk(r.data)).catch(() => {})
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = (text: string) => {
    const q = text.trim()
    if (!q || streaming) return
    setInput('')
    send(q)
  }

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(input) }
  }

  return (
    <div className="flex h-screen bg-snow">
      <Sidebar />

      <div className="flex-1 flex flex-col min-w-0">
        <div className="border-b border-arctic-mist px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-carbon">Analytics Chat</h2>
            <p className="text-xs text-pewter mt-0.5">
              Ask anything about Excelsis360 data in natural language
            </p>
          </div>
          {messages.length > 0 && (
            <button
              onClick={clearHistory}
              className="text-xs text-pewter hover:text-carbon transition-colors underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-link-blue rounded"
            >
              Clear history
            </button>
          )}
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-8" aria-live="polite" aria-label="Conversation">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center">
              <h3 className="font-serif text-xl font-normal text-carbon mb-2">
                Where should we begin?
              </h3>
              <p className="text-sm text-pewter mb-8">
                Start by asking a question or try one of these
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-xl">
                {buildSuggestions(atRisk, summary).map((s) => (
                  <button
                    key={s}
                    onClick={() => handleSend(s)}
                    className="text-left text-sm text-pewter bg-fog border border-arctic-mist hover:border-pewter hover:text-carbon px-4 py-3 rounded-[10px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-link-blue focus-visible:ring-offset-2"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map((m, i) => <MessageBubble key={i} msg={m} />)}
              <div ref={bottomRef} />
            </>
          )}
        </div>

        <div className="border-t border-arctic-mist px-6 py-4">
          <div className="flex items-end gap-3 bg-fog border border-arctic-mist rounded-input px-5 py-3 focus-within:ring-2 focus-within:ring-link-blue">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKey}
              disabled={streaming}
              rows={1}
              placeholder="Ask anything about your data…"
              className="flex-1 bg-transparent text-sm text-carbon placeholder-pewter resize-none focus:outline-none max-h-32"
              style={{ lineHeight: '1.5' }}
            />
            <button
              onClick={() => handleSend(input)}
              disabled={streaming || !input.trim()}
              className="bg-carbon text-white disabled:opacity-30 rounded-pill px-4 py-1.5 text-sm transition-opacity hover:opacity-90 flex-shrink-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-link-blue focus-visible:ring-offset-2"
            >
              {streaming ? '…' : 'Send'}
            </button>
          </div>
          <p className="text-xs text-pewter mt-2 text-center">
            Enter to send · Shift+Enter for newline
          </p>
        </div>
      </div>
    </div>
  )
}
