import { KeyboardEvent, useState } from 'react'
import AttemptCard from './components/AttemptCard'
import { useTaskRun } from './lib/useTaskRun'

export default function App() {
  const { attempts, finalResult, running, error, run } = useTaskRun()
  const [input, setInput] = useState('')

  const handleRun = () => {
    if (!input.trim() || running) return
    run(input)
  }

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleRun() }
  }

  return (
    <div className="min-h-screen bg-snow">
      <header className="border-b border-arctic-mist px-6 py-4">
        <p className="text-xs text-pewter uppercase tracking-widest mb-1">PySpark AI Agent</p>
        <h1 className="text-sm text-carbon font-semibold">Coding agent — writes, runs, and self-repairs PySpark</h1>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-8">
        <div className="flex items-end gap-3 bg-fog border border-arctic-mist rounded-[10px] px-5 py-3 focus-within:ring-2 focus-within:ring-link-blue mb-8">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKey}
            disabled={running}
            rows={2}
            placeholder="Describe a PySpark task, e.g. 'What is the average order value by region?'"
            className="flex-1 bg-transparent text-sm text-carbon placeholder-pewter resize-none focus:outline-none"
          />
          <button
            onClick={handleRun}
            disabled={running || !input.trim()}
            className="bg-carbon text-white disabled:opacity-30 rounded-pill px-4 py-1.5 text-sm transition-opacity hover:opacity-90 flex-shrink-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-link-blue focus-visible:ring-offset-2"
          >
            {running ? 'Running…' : 'Run'}
          </button>
        </div>

        {error && (
          <div className="mb-6 text-sm text-danger border border-danger/30 bg-red-50 rounded-[10px] px-4 py-3">
            {error}
          </div>
        )}

        {attempts.length === 0 && !running && !finalResult && !error && (
          <p className="text-sm text-pewter text-center py-16">
            Attempts and their execution results will appear here as the agent runs.
          </p>
        )}

        {attempts.map((a) => (
          <AttemptCard key={a.step} attempt={a} />
        ))}

        {finalResult && (
          <div className="mt-6 border border-link-blue/30 rounded-[10px] overflow-hidden">
            <div className="bg-fog px-4 py-2 border-b border-arctic-mist">
              <span className="text-xs font-medium text-carbon">Final result</span>
            </div>
            <div className="px-4 py-3 text-sm text-carbon whitespace-pre-wrap font-mono">
              {finalResult}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
