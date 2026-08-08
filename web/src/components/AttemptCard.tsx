import { Attempt } from '../types'

interface Props {
  attempt: Attempt
}

export default function AttemptCard({ attempt }: Props) {
  const settled  = attempt.output !== undefined || attempt.error !== undefined
  const succeeded = settled && !attempt.error

  return (
    <div className="border border-arctic-mist rounded-[10px] overflow-hidden mb-4">
      <div className="flex items-center justify-between bg-fog px-4 py-2 border-b border-arctic-mist">
        <span className="text-xs font-medium text-carbon">Attempt {attempt.step}</span>
        <span
          className={`text-xs px-2 py-0.5 rounded-pill border ${
            !settled
              ? 'border-arctic-mist text-pewter'
              : succeeded
                ? 'border-success text-success'
                : 'border-danger text-danger'
          }`}
        >
          {!settled ? 'running…' : succeeded ? 'succeeded' : 'failed'}
        </span>
      </div>

      <pre className="bg-carbon text-white text-xs leading-relaxed p-4 overflow-x-auto font-mono">
        <code>{attempt.code}</code>
      </pre>

      {attempt.error && (
        <div className="px-4 py-3 text-xs font-mono text-danger bg-red-50 border-t border-arctic-mist whitespace-pre-wrap">
          {attempt.error}
        </div>
      )}
      {attempt.output && (
        <div className="px-4 py-3 text-xs font-mono text-carbon whitespace-pre-wrap border-t border-arctic-mist">
          {attempt.output}
        </div>
      )}
    </div>
  )
}
