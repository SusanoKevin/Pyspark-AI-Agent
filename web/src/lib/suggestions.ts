import { AlertItem, DataSummary } from '../types'

export function buildSuggestions(
  atRisk: AlertItem[],
  summary: DataSummary | null,
): string[] {
  const out: string[] = []

  if (atRisk.length > 0) {
    const worst = atRisk[0]
    const name = worst.label ?? `Entity #${worst.entity_id}`
    out.push(`Why is ${name} below the threshold?`)
  }

  if ((summary?.dimensions?.length ?? 0) > 0) {
    out.push('Which segment has the lowest metric rate this month?')
  }

  out.push('Show me entities below the threshold')
  out.push('Compare this month vs last month')

  return out.slice(0, 4)
}
