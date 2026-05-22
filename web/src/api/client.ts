import axios from 'axios'
import { DashboardFilterEvent } from '../types'

const api = axios.create({ baseURL: '/' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.clear()
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api

export async function streamChat(
  message: string,
  onToken:           (t: string) => void,
  onToolStart:       (tool: string) => void,
  onToolEnd:         (tool: string) => void,
  onDone:            () => void,
  onError:           (msg: string) => void,
  onDashboardFilter?: (f: DashboardFilterEvent) => void,
) {
  const token = localStorage.getItem('token')
  const res = await fetch('/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ message }),
  })

  if (!res.ok) { onError(`Request failed: ${res.status}`); return }
  if (!res.body) { onError('Stream unavailable'); return }

  const reader  = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) { onDone(); break }

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const raw = line.slice(6).trim()
      if (!raw) continue
      try {
        const evt = JSON.parse(raw)
        if      (evt.type === 'token')            onToken(evt.content)
        else if (evt.type === 'tool_start')       onToolStart(evt.tool)
        else if (evt.type === 'tool_end')         onToolEnd(evt.tool)
        else if (evt.type === 'done')             onDone()
        else if (evt.type === 'error')            onError(evt.message)
        else if (evt.type === 'dashboard_filter') onDashboardFilter?.({
          classes: evt.classes ?? [],
          period:  evt.period  ?? 'all',
          view:    evt.view    ?? 'overview',
        })
      } catch { /* ignore malformed SSE lines */ }
    }
  }
}
