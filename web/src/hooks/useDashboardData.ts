import { useEffect, useState } from 'react'
import api from '../api/client'
import {
  AlertItem,
  DataSummary,
  DashboardFilter,
  DimensionStat,
  GroupStat,
  StatusCount,
  WeeklyStat,
} from '../types'

export interface DashboardData {
  summary:      DataSummary | null
  classStats:   GroupStat[]
  weeklyStats:  WeeklyStat[]
  dowStats:     DimensionStat[]
  statusCounts: StatusCount[]
  atRisk:       AlertItem[]
  sparklines:   Record<string, (number | null)[]>
  trends:       { current: WeeklyStat[]; previous: WeeklyStat[] }
  loading:      boolean
  error:        string | null
}

const INITIAL: DashboardData = {
  summary:      null,
  classStats:   [],
  weeklyStats:  [],
  dowStats:     [],
  statusCounts: [],
  atRisk:       [],
  sparklines:   {},
  trends:       { current: [], previous: [] },
  loading:      true,
  error:        null,
}

function deriveThresholdBreakdown(groupStats: GroupStat[]): StatusCount[] {
  const totals = groupStats.reduce(
    (acc, row) => ({
      total:          acc.total          + row.total,
      positive_count: acc.positive_count + row.positive_count,
    }),
    { total: 0, positive_count: 0 }
  )
  const below = Math.max(0, totals.total - totals.positive_count)
  return [
    { name: 'Above threshold', value: totals.positive_count, color: '#00a86b' },
    { name: 'Below threshold', value: below,                  color: '#e74c3c' },
  ]
}

function buildParams(filter: DashboardFilter): Record<string, string> {
  const params: Record<string, string> = {
    classes: filter.classes.join(','),
    period:  filter.period,
  }
  if (filter.period === 'custom') {
    if (filter.date_from) params.date_from = filter.date_from
    if (filter.date_to)   params.date_to   = filter.date_to
  }
  return params
}

export function useDashboardData(filter: DashboardFilter): DashboardData {
  const [data, setData] = useState<DashboardData>(INITIAL)

  const filterKey = `${filter.classes.join(',')}|${filter.period}|${filter.date_from ?? ''}|${filter.date_to ?? ''}`

  useEffect(() => {
    const controller = new AbortController()
    const { signal } = controller
    const params = buildParams(filter)

    setData((d) => ({ ...d, loading: true, error: null }))

    Promise.all([
      api.get('/data/summary',  { signal }),
      api.get('/data/stats',    { params: { ...params, group_by: 'class'       }, signal }),
      api.get('/data/stats',    { params: { ...params, group_by: 'week'        }, signal }),
      api.get('/data/stats',    { params: { ...params, group_by: 'day_of_week' }, signal }),
      api.get('/data/alerts',   { params: { ...params, threshold: 75 }, signal }),
    ])
      .then(([summaryRes, classRes, weekRes, dowRes, alertsRes]) => {
        if (signal.aborted) return
        const atRisk: AlertItem[]     = alertsRes.data
        const classStats: GroupStat[] = classRes.data

        setData({
          summary:      summaryRes.data,
          classStats,
          weeklyStats:  weekRes.data,
          dowStats:     dowRes.data,
          statusCounts: deriveThresholdBreakdown(classStats),
          atRisk,
          sparklines:   {},
          trends:       { current: [], previous: [] },
          loading:      false,
          error:        null,
        })

        if (atRisk.length > 0) {
          const ids = atRisk.map((s) => s.entity_id).join(',')
          api.get('/data/sparklines', { params: { ids }, signal })
            .then((r) => { if (!signal.aborted) setData((d) => ({ ...d, sparklines: r.data })) })
            .catch(() => {})
        }

        api.get('/data/trends', { params: { classes: params.classes }, signal })
          .then((r) => { if (!signal.aborted) setData((d) => ({ ...d, trends: r.data })) })
          .catch(() => {})
      })
      .catch(() => {
        if (!signal.aborted)
          setData((d) => ({ ...d, loading: false, error: 'Failed to load dashboard data' }))
      })

    return () => controller.abort()
  }, [filterKey]) // eslint-disable-line react-hooks/exhaustive-deps

  return data
}
