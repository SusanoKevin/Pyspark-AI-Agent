import { useEffect, useState } from 'react'
import { streamChat } from '../api/client'
import { DashboardFilterEvent, Message } from '../types'

const STORAGE_KEY = 'excelsis_data_chat'

function loadHistory(): Message[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export function useChat(onDashboardFilter?: (f: DashboardFilterEvent) => void) {
  const [messages, setMessages] = useState<Message[]>(loadHistory)
  const [streaming, setStreaming] = useState(false)

  useEffect(() => {
    try {
      const toSave = messages.map((m) => ({ ...m, isStreaming: false }))
      localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave))
    } catch {
      // localStorage full — ignore
    }
  }, [messages])

  const updateLast = (patch: Partial<Message>) =>
    setMessages((prev) => {
      const msgs = [...prev]
      msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], ...patch }
      return msgs
    })

  const send = async (q: string) => {
    if (!q.trim() || streaming) return
    setStreaming(true)
    setMessages((prev) => [...prev, { role: 'user', content: q, toolsUsed: [] }])
    setMessages((prev) => [...prev, { role: 'assistant', content: '', toolsUsed: [], isStreaming: true }])

    await streamChat(
      q,
      (token) => setMessages((prev) => {
        const msgs = [...prev]
        const last = msgs[msgs.length - 1]
        msgs[msgs.length - 1] = { ...last, content: last.content + token }
        return msgs
      }),
      (tool) => setMessages((prev) => {
        const msgs = [...prev]
        const last = msgs[msgs.length - 1]
        if (!last.toolsUsed.includes(tool))
          msgs[msgs.length - 1] = { ...last, toolsUsed: [...last.toolsUsed, tool] }
        return msgs
      }),
      () => {},
      () => { updateLast({ isStreaming: false }); setStreaming(false) },
      (msg) => { updateLast({ content: msg, isStreaming: false }); setStreaming(false) },
      (f) => { updateLast({ dashboardFilter: f }); onDashboardFilter?.(f) },
    )
  }

  const clearHistory = () => {
    setMessages([])
    localStorage.removeItem(STORAGE_KEY)
  }

  return { messages, streaming, send, clearHistory }
}
