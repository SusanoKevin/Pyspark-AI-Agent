import { useState } from 'react'

export interface ChartSelection {
  group?:     string
  week?:      string
  dayOfWeek?: string
  threshold?: 'above' | 'below'
}

export function useChartSelection() {
  const [selection, setSelection] = useState<ChartSelection>({})

  function select(patch: Partial<ChartSelection>) {
    setSelection((prev) => {
      const next: ChartSelection = { ...prev }
      for (const key of Object.keys(patch) as (keyof ChartSelection)[]) {
        if (prev[key] === patch[key]) {
          delete next[key]
        } else {
          (next as Record<string, unknown>)[key] = patch[key]
        }
      }
      return next
    })
  }

  function clearSelection() {
    setSelection({})
  }

  const hasSelection = Object.keys(selection).length > 0

  return { selection, select, clearSelection, hasSelection }
}
