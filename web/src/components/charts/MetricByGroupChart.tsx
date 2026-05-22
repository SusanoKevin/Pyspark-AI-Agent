import { useRef } from 'react'
import {
  Bar, BarChart, CartesianGrid, Cell, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { GroupStat } from '../../types'

interface Props {
  data:          GroupStat[]
  selectedGroup?: string
  onSelect:      (cls: string) => void
  onClassDrill:  (cls: string) => void
  loading:       boolean
}

function rateColor(rate: number): string {
  if (rate < 70) return '#e74c3c'
  if (rate < 80) return '#f5a623'
  return '#00a86b'
}

function CustomTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null
  const d: GroupStat = payload[0].payload
  return (
    <div className="bg-fog border border-arctic-mist rounded-[10px] p-3 text-xs shadow-sm">
      <p className="font-semibold text-carbon mb-1">{d.class}</p>
      <p className="text-pewter">Rate: <span className="text-carbon font-mono">{d.metric_rate}%</span></p>
      <p className="text-pewter">Above threshold: <span className="text-carbon font-mono">{d.positive_count}</span></p>
    </div>
  )
}

export default function MetricByGroupChart({ data, selectedGroup, onSelect, onClassDrill, loading }: Props) {
  const clickTimers = useRef<Record<string, ReturnType<typeof setTimeout>>>({})
  const sorted = [...data].sort((a, b) => a.metric_rate - b.metric_rate)
  const height  = Math.max(280, sorted.length * 44 + 80)

  function handleClick(cls: string) {
    if (clickTimers.current[cls]) return
    clickTimers.current[cls] = setTimeout(() => {
      delete clickTimers.current[cls]
      onSelect(cls)
    }, 230)
  }

  function handleDoubleClick(cls: string) {
    clearTimeout(clickTimers.current[cls])
    delete clickTimers.current[cls]
    onClassDrill(cls)
  }

  if (loading) {
    return (
      <div className="space-y-2 animate-pulse">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-8 bg-arctic-mist rounded" />
        ))}
      </div>
    )
  }

  if (!data.length) return <p className="text-xs text-pewter py-4">No data available.</p>

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={sorted} layout="vertical" margin={{ left: 72, right: 32, top: 8, bottom: 8 }}>
        <CartesianGrid horizontal={false} stroke="#ececec" />
        <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11, fill: '#5d5d5d' }} />
        <YAxis type="category" dataKey="class" tick={{ fontSize: 12, fill: '#0d0d0d' }} width={68} />
        <ReferenceLine x={75} stroke="#e74c3c" strokeDasharray="3 3"
          label={{ value: '75%', fill: '#e74c3c', fontSize: 10, position: 'insideTopRight' }} />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(0,0,0,0.04)' }} />
        <Bar dataKey="metric_rate" radius={[0, 4, 4, 0]}>
          {sorted.map((entry) => (
            <Cell
              key={entry.class}
              fill={selectedGroup && selectedGroup !== entry.class ? '#ececec' : rateColor(entry.metric_rate)}
              cursor="pointer"
              onClick={() => handleClick(entry.class)}
              onDoubleClick={() => handleDoubleClick(entry.class)}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
