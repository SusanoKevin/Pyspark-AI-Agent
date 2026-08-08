// ── Streamed trace events (mirrors api/routers/task.py SSE payloads) ──────────

export interface CodeAttemptEvent {
  type: 'code_attempt'
  step: number
  code: string
}

export interface ExecutionResultEvent {
  type:   'execution_result'
  step:   number
  output?: string
  error?:  string
}

export interface FinalResultEvent {
  type:   'final_result'
  result: string
}

export interface ErrorEvent {
  type:    'error'
  message: string
}

export interface DoneEvent {
  type: 'done'
}

export type StreamEvent =
  | CodeAttemptEvent
  | ExecutionResultEvent
  | FinalResultEvent
  | ErrorEvent
  | DoneEvent

// ── Client-side aggregated view of one code_attempt + its result ──────────────

export interface Attempt {
  step:    number
  code:    string
  output?: string
  error?:  string
}
