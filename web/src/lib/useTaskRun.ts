import { useState } from 'react'
import { streamTask } from '../api/client'
import { Attempt, StreamEvent } from '../types'

export function useTaskRun() {
  const [attempts, setAttempts]   = useState<Attempt[]>([])
  const [finalResult, setResult]  = useState<string | null>(null)
  const [running, setRunning]     = useState(false)
  const [error, setError]         = useState<string | null>(null)

  const applyEvent = (evt: StreamEvent) => {
    if (evt.type === 'code_attempt') {
      setAttempts((prev) => [...prev, { step: evt.step, code: evt.code }])
      return
    }
    if (evt.type === 'execution_result') {
      setAttempts((prev) =>
        prev.map((a) => (a.step === evt.step ? { ...a, output: evt.output, error: evt.error } : a)),
      )
      return
    }
    if (evt.type === 'final_result') {
      setResult(evt.result)
    }
  }

  const run = async (task: string) => {
    const trimmed = task.trim()
    if (!trimmed || running) return

    setRunning(true)
    setAttempts([])
    setResult(null)
    setError(null)

    await streamTask(
      trimmed,
      applyEvent,
      () => setRunning(false),
      (message) => { setError(message); setRunning(false) },
    )
  }

  return { attempts, finalResult, running, error, run }
}
