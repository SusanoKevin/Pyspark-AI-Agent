import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { StatusCount } from '../../types'

interface Props {
  data:               StatusCount[]
  loading:            boolean
  selectedThreshold?: 'above' | 'below'
  onSelect?:          (t: 'above' | 'below') => void
}

function nameToThreshold(name: string): 'above' | 'below' | null {
  const n = name.toLowerCase()
  if (n.includes('above')) return 'above'
  if (n.includes('below')) return 'below'
  return null
}

export default function MetricBreakdownChart({ data, loading, selectedThreshold, onSelect }: Props) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-48">
        <div className="w-32 h-32 rounded-full border-8 border-arctic-mist animate-pulse" />
      </div>
    )
  }
  if (!data.length || data.every((d) => d.value === 0)) {
    return <p className="text-xs text-pewter py-4">No data available.</p>
  }

  return (
    <ResponsiveContainer width="100%" height={240}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          innerRadius="52%"
          outerRadius="78%"
          paddingAngle={2}
          cursor={onSelect ? 'pointer' : 'default'}
          onClick={(entry) => {
            const t = nameToThreshold(entry.name ?? '')
            if (t && onSelect) onSelect(t)
          }}
        >
          {data.map((entry, i) => {
            const t = nameToThreshold(entry.name)
            const dimmed = selectedThreshold !== undefined && t !== selectedThreshold
            return <Cell key={i} fill={entry.color} fillOpacity={dimmed ? 0.25 : 1} />
          })}
        </Pie>
        <Tooltip
          formatter={(v, n) => [(typeof v === 'number' ? v : 0).toLocaleString(), String(n ?? '')]}
          contentStyle={{ fontSize: 12, borderRadius: 10, border: '1px solid #ececec' }}
        />
        <Legend
          iconType="circle"
          iconSize={8}
          formatter={(v) => <span className="text-xs text-pewter">{v}</span>}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}
