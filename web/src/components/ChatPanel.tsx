import { KeyboardEvent, useEffect, useRef, useState } from 'react'
import MessageBubble from './MessageBubble'
import { AlertItem, DataSummary, DashboardFilterEvent } from '../types'
import { buildSuggestions } from '../lib/suggestions'
import { useChat } from '../lib/useChat'

interface Props {
  atRisk:              AlertItem[]
  summary:             DataSummary | null
  onClose:             () => void
  onDashboardFilter?:  (f: DashboardFilterEvent) => void
}

export default function ChatPanel({ atRisk, summary, onClose, onDashboardFilter }: Props) {
  const { messages, streaming, send, clearHistory } = useChat(onDashboardFilter)
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const suggestions = buildSuggestions(atRisk, summary)

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
    <aside className="w-80 flex-shrink-0 border-l border-arctic-mist flex flex-col bg-snow">

      <div className="px-4 py-3 border-b border-arctic-mist flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-carbon">Ask Excelsis</p>
          <p className="text-xs text-pewter mt-0.5">AI data analyst</p>
        </div>
        <div className="flex items-center gap-2">
          {messages.length > 0 && (
            <button
              onClick={clearHistory}
              className="text-xs text-pewter hover:text-carbon transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-link-blue rounded"
            >
              Clear
            </button>
          )}
          <button
            onClick={onClose}
            aria-label="Close chat panel"
            className="text-pewter hover:text-carbon transition-colors w-7 h-7 flex items-center justify-center rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-link-blue"
          >
            ✕
          </button>
        </div>
      </div>

      <div
        className="flex-1 overflow-y-auto px-4 py-4"
        aria-live="polite"
        aria-label="Conversation"
      >
        {messages.length === 0 ? (
          <div className="space-y-2">
            <p className="text-xs text-pewter uppercase tracking-widest mb-3">Suggested</p>
            {suggestions.map((s) => (
              <button
                key={s}
                onClick={() => handleSend(s)}
                className="w-full text-left text-sm text-pewter bg-fog border border-arctic-mist hover:border-pewter hover:text-carbon px-3 py-2.5 rounded-[10px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-link-blue focus-visible:ring-offset-2"
              >
                {s}
              </button>
            ))}
          </div>
        ) : (
          <>
            {messages.map((m, i) => <MessageBubble key={i} msg={m} />)}
            <div ref={bottomRef} />
          </>
        )}
      </div>

      <div className="border-t border-arctic-mist px-4 py-3">
        <div className="flex items-end gap-2 bg-fog border border-arctic-mist rounded-[10px] px-4 py-2 focus-within:ring-2 focus-within:ring-link-blue">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKey}
            disabled={streaming}
            rows={1}
            placeholder="Ask anything about your data…"
            className="flex-1 bg-transparent text-sm text-carbon placeholder-pewter resize-none focus:outline-none max-h-28"
            style={{ lineHeight: '1.5' }}
          />
          <button
            onClick={() => handleSend(input)}
            disabled={streaming || !input.trim()}
            className="bg-carbon text-white disabled:opacity-30 rounded-pill px-3 py-1 text-xs flex-shrink-0 hover:opacity-90 transition-opacity focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-link-blue focus-visible:ring-offset-2"
          >
            {streaming ? '…' : 'Send'}
          </button>
        </div>
        <p className="text-xs text-pewter mt-1.5 text-center">Enter to send · Shift+Enter for newline</p>
      </div>

    </aside>
  )
}
