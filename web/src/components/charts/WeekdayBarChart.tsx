import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { DimensionStat } from '../../types'

interface Props {
  data:         DimensionStat[]
  loading:      boolean
  selectedDay?: string
  onSelect?:    (day: string) => void
}

const DAY_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

function rateColor(rate: number): string {
  if (rate < 70) return '#e74c3c'
  if (rate < 80) return '#f5a623'
  return '#00a86b'
}

export default function WeekdayBarChart({ data, loading, selectedDay, onSelect }: Props) {
  if (loading) return <div className="h-48 bg-arctic-mist rounded animate-pulse" />
  if (!data.length) return <p className="text-xs text-pewter py-4">No data available.</p>

  const ordered = DAY_ORDER
    .map((d) => data.find((r) => r.day_of_week === d))
    .filter(Boolean) as DimensionStat[]

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={ordered} margin={{ left: 8, right: 16, top: 8, bottom: 8 }}>
        <CartesianGrid vertical={false} stroke="#ececec" />
        <XAxis
          dataKey="day_of_week"
          tickFormatter={(d) => d.slice(0, 3)}
          tick={{ fontSize: 11, fill: '#5d5d5d' }}
        />
        <YAxis
          domain={[0, 100]}
          tickFormatter={(v) => `${v}%`}
          tick={{ fontSize: 11, fill: '#5d5d5d' }}
          width={40}
        />
        <ReferenceLine y={75} stroke="#e74c3c" strokeDasharray="3 3" />
        <Tooltip
          formatter={(v) => [`${typeof v === 'number' ? v : ''}%`, 'Rate']}
          contentStyle={{ fontSize: 12, borderRadius: 10, border: '1px solid #ececec' }}
        />
        <Bar dataKey="metric_rate" radius={[4, 4, 0, 0]} cursor={onSelect ? 'pointer' : 'default'}>
          {ordered.map((d, i) => (
            <Cell
              key={i}
              fill={selectedDay && selectedDay !== d.day_of_week ? '#ececec' : rateColor(d.metric_rate)}
              onClick={() => onSelect?.(d.day_of_week)}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
