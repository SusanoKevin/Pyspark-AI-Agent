export interface AuthUser {
  token:  string
  userId: string
}

// ── Dashboard filter / drill state ────────────────────────────────────────────

export type DashboardPeriod = 'all' | 'last_7_days' | 'last_30_days' | 'custom'
export type DrillLevel      = 'overview' | 'group' | 'entity'

export interface DashboardFilter {
  classes:    string[]
  period:     DashboardPeriod
  date_from?: string
  date_to?:   string
}

export interface DashboardFilterEvent {
  classes: string[]
  period:  DashboardPeriod
  view:    DrillLevel
}

// ── Chart data row shapes ─────────────────────────────────────────────────────

export interface GroupStat {
  class:          string
  total:          number
  positive_count: number
  metric_rate:    number
}

export interface WeeklyStat {
  week:           string
  total:          number
  positive_count: number
  metric_rate:    number
}

export interface DimensionStat {
  day_of_week:    string
  total:          number
  positive_count: number
  metric_rate:    number
}

export interface StatusCount {
  name:  string
  value: number
  color: string
}

// ── Messaging ─────────────────────────────────────────────────────────────────

export interface Message {
  role:             'user' | 'assistant'
  content:          string
  toolsUsed:        string[]
  isStreaming?:     boolean
  dashboardFilter?: DashboardFilterEvent
}

// ── API response shapes ───────────────────────────────────────────────────────

export interface DataSummary {
  total_records:         number
  entity_count:          number
  date_range:            { from: string; to: string }
  metric_rate:           number
  below_threshold_count: number
  dimensions:            string[]
}

export interface StatsRow {
  [key: string]: string | number
  metric_rate: number
}

export interface AlertItem {
  entity_id:      number
  label?:         string
  group_name?:    string
  total:          number
  positive_count: number
  metric_rate:    number
}
