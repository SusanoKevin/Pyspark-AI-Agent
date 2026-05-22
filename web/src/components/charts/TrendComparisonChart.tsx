import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { WeeklyStat } from '../../types'

interface Props {
  current:       WeeklyStat[]
  previous:      WeeklyStat[]
  loading:       boolean
  selectedWeek?: string
  onSelect?:     (week: string) => void
}

export default function TrendComparisonChart({ current, previous, loading, selectedWeek, onSelect }: Props) {
  if (loading) return <div className="h-48 animate-pulse bg-arctic-mist/50 rounded" />

  const allWeeks = Array.from(
    new Set([...current.map((r) => r.week), ...previous.map((r) => r.week)])
  ).sort()

  const chartData = allWeeks.map((week) => ({
    week,
    current:  current.find((r)  => r.week === week)?.metric_rate ?? null,
    previous: previous.find((r) => r.week === week)?.metric_rate ?? null,
  }))

  if (chartData.length === 0) {
    return <p className="text-xs text-pewter">No trend data available for this period.</p>
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e8eaed" />
        <XAxis dataKey="week" tick={{ fontSize: 10 }} />
        <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} unit="%" />
        <Tooltip formatter={(v: unknown) => v !== null ? `${v}%` : '—'} />
        <Legend />
        {selectedWeek && (
          <ReferenceLine x={selectedWeek} stroke="#007aff" strokeDasharray="3 3"
            label={{ value: '▼', fill: '#007aff', fontSize: 10, position: 'top' }} />
        )}
        <Line
          type="monotone"
          dataKey="current"
          stroke="#00a86b"
          name="Last 30 days"
          dot={false}
          strokeWidth={2}
          connectNulls
          activeDot={{ r: 5, cursor: onSelect ? 'pointer' : 'default',
            onClick: (_: unknown, payload: any) => onSelect?.(payload?.activePayload?.[0]?.payload?.week) }}
        />
        <Line
          type="monotone"
          dataKey="previous"
          stroke="#9b9b9b"
          name="Prior 30 days"
          dot={false}
          strokeWidth={1.5}
          strokeDasharray="4 2"
          connectNulls
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
