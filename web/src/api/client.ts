import { StreamEvent } from '../types'

export async function streamTask(
  task: string,
  onEvent: (event: StreamEvent) => void,
  onDone: () => void,
  onError: (message: string) => void,
) {
  const res = await fetch('/task', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task }),
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
        const evt = JSON.parse(raw) as StreamEvent
        if (evt.type === 'done') { onDone(); continue }
        if (evt.type === 'error') { onError(evt.message); continue }
        onEvent(evt)
      } catch {
        /* ignore malformed SSE lines */
      }
    }
  }
}
