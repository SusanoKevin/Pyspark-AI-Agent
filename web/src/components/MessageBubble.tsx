import { DashboardFilterEvent, Message } from '../types'

const TOOL_LABELS: Record<string, string> = {
  query_data:            'Querying data…',
  get_threshold_alerts:  'Finding threshold alerts…',
  get_summary:           'Summary',
  update_dashboard_view: 'Dashboard filter',
  run_sql_query:         'SQL query',
  compare_periods:       'Period comparison',
  compare_segments:      'Comparing segments…',
}

function buildDashboardUrl(f: DashboardFilterEvent): string {
  const params = new URLSearchParams()
  if (f.classes.length > 0) params.set('classes', f.classes.join(','))
  if (f.period !== 'all') params.set('period', f.period)
  if (f.view === 'group') params.set('view', f.view)
  const qs = params.toString()
  return `/dashboard${qs ? `?${qs}` : ''}`
}

interface Props { msg: Message }

export default function MessageBubble({ msg }: Props) {
  const isUser = msg.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-5`}>
      <div className={`max-w-[78%] ${isUser ? 'order-1' : 'order-2'}`}>

        {!isUser && msg.toolsUsed.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2">
            {msg.toolsUsed.map((t, i) => (
              <span
                key={i}
                className="text-xs px-2.5 py-0.5 rounded-pill border border-arctic-mist text-pewter bg-fog"
              >
                {TOOL_LABELS[t] ?? t}
              </span>
            ))}
          </div>
        )}

        <div
          className={`px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
            isUser
              ? 'bg-carbon text-white rounded-2xl rounded-tr-sm'
              : 'bg-fog text-carbon rounded-2xl rounded-tl-sm border border-arctic-mist'
          } ${msg.isStreaming ? 'cursor-blink' : ''}`}
        >
          {msg.content || (msg.isStreaming ? '' : '…')}
        </div>

        {!isUser && msg.dashboardFilter && (
          <div className="mt-3">
            <a
              href={buildDashboardUrl(msg.dashboardFilter)}
              className="inline-flex items-center gap-2 text-sm bg-fog border border-arctic-mist hover:border-pewter text-carbon rounded-[10px] px-4 py-2 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-link-blue"
            >
              View in Dashboard ↗
            </a>
          </div>
        )}

      </div>
    </div>
  )
}
