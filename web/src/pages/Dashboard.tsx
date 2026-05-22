import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import ChatPanel from '../components/ChatPanel'
import FilterBar from '../components/FilterBar'
import Breadcrumb from '../components/Breadcrumb'
import DrilldownPanel from '../components/DrilldownPanel'
import MetricByGroupChart from '../components/charts/MetricByGroupChart'
import WeeklyTrendChart from '../components/charts/WeeklyTrendChart'
import MetricBreakdownChart from '../components/charts/MetricBreakdownChart'
import WeekdayBarChart from '../components/charts/WeekdayBarChart'
import TrendComparisonChart from '../components/charts/TrendComparisonChart'
import { useDashboardData } from '../hooks/useDashboardData'
import { useChartSelection } from '../hooks/useChartSelection'
import { DashboardFilter, DashboardFilterEvent, DashboardPeriod, DrillLevel } from '../types'

function KpiCard({ label, value, sub, featured }: {
  label: string; value: string; sub?: string; featured?: boolean
}) {
  return (
    <div className={`bg-fog rounded-[10px] p-5 ${
      featured
        ? 'border border-arctic-mist border-l-4 border-l-carbon'
        : 'border border-arctic-mist'
    }`}>
      <p className="text-xs text-pewter uppercase tracking-widest mb-3">{label}</p>
      <p className={`text-carbon font-semibold ${featured ? 'text-4xl' : 'text-2xl'}`}>{value}</p>
      {sub && <p className="text-xs text-pewter mt-1">{sub}</p>}
    </div>
  )
}

export default function Dashboard() {
  const [searchParams] = useSearchParams()

  const [filter, setFilter]         = useState<DashboardFilter>({ classes: [], period: 'all' })
  const [drillLevel, setDrillLevel] = useState<DrillLevel>('overview')
  const { selection, select, clearSelection, hasSelection } = useChartSelection()
  const [drillClass, setDrillClass]   = useState<string | null>(null)
  const [drillStudent, setDrillStudent] = useState<number | null>(null)
  const [panelOpen, setPanel]          = useState(false)

  // URL param initialization for "View in Dashboard" deep links
  useEffect(() => {
    const cls  = searchParams.get('classes')
    const per  = searchParams.get('period') as DashboardPeriod | null
    const view = searchParams.get('view')   as DrillLevel | null
    if (cls || per || view) {
      const classes = cls?.split(',').filter(Boolean) ?? []
      setFilter({ classes, period: per ?? 'all' })
      if (view === 'group' && classes.length > 0) {
        setDrillLevel('group')
        setDrillClass(classes[0])
        select({ group: classes[0] })
      }
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const { summary, classStats, weeklyStats, dowStats, statusCounts, atRisk, sparklines, trends, loading } =
    useDashboardData(filter)

  const availableClasses = summary?.dimensions ?? []

  function handleClassClick(cls: string) {
    select({ group: cls })
  }

  function handleClassDrill(cls: string) {
    setDrillLevel('group')
    setDrillClass(cls)
    select({ group: cls })
    setFilter((f) => ({ ...f, classes: [cls] }))
  }

  function handleInspect(entityId: number) {
    setDrillLevel('entity')
    setDrillStudent(entityId)
  }

  function handleBreadcrumb(level: DrillLevel) {
    setDrillLevel(level)
    if (level === 'overview') {
      setDrillClass(null)
      setDrillStudent(null)
      clearSelection()
      setFilter((f) => ({ ...f, classes: [] }))
    } else if (level === 'group') {
      setDrillStudent(null)
    }
  }

  function handleAgentFilter(f: DashboardFilterEvent) {
    setFilter({ classes: f.classes, period: f.period })
    if (f.classes[0]) select({ group: f.classes[0] }); else clearSelection()
    if (f.view === 'group' && f.classes.length > 0) {
      setDrillLevel('group')
      setDrillClass(f.classes[0])
    } else if (f.view === 'overview') {
      setDrillLevel('overview')
      setDrillClass(null)
      setDrillStudent(null)
    }
  }

  const entityName = drillStudent !== null
    ? atRisk.find((s) => s.entity_id === drillStudent)?.label
    : undefined

  return (
    <div className="flex h-screen bg-snow">
      <Sidebar />

      <div className="flex-1 overflow-y-auto px-6 py-8 min-w-0">

        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <h2 className="font-serif text-2xl font-normal text-carbon">Data Dashboard</h2>
            {summary?.date_range && (
              <p className="text-xs text-pewter mt-1">
                {summary.date_range.from} — {summary.date_range.to}
              </p>
            )}
          </div>
          <button
            onClick={() => setPanel((p) => !p)}
            className={`text-sm rounded-[10px] px-4 py-2 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-link-blue focus-visible:ring-offset-2 ${
              panelOpen
                ? 'bg-arctic-mist text-carbon'
                : 'bg-fog border border-arctic-mist text-pewter hover:text-carbon hover:border-pewter'
            }`}
          >
            {panelOpen ? 'Close chat' : 'Ask Excelsis'}
          </button>
        </div>

        {/* Filter bar */}
        <div className="mb-4">
          <FilterBar filter={filter} classes={availableClasses} onChange={setFilter} />
        </div>

        {/* Selection chips */}
        {hasSelection && (
          <div className="flex items-center gap-2 flex-wrap mb-5">
            <span className="text-xs text-pewter uppercase tracking-widest">Filtering:</span>
            {selection.group && (
              <span className="inline-flex items-center gap-1 text-xs bg-arctic-mist text-carbon rounded-pill px-3 py-1">
                Group: {selection.group}
                <button onClick={() => select({ group: selection.group })} className="ml-1 hover:text-danger focus-visible:outline-none" aria-label="Remove group filter">✕</button>
              </span>
            )}
            {selection.threshold && (
              <span className="inline-flex items-center gap-1 text-xs bg-arctic-mist text-carbon rounded-pill px-3 py-1">
                {selection.threshold === 'above' ? 'Above threshold' : 'Below threshold'}
                <button onClick={() => select({ threshold: selection.threshold })} className="ml-1 hover:text-danger focus-visible:outline-none" aria-label="Remove threshold filter">✕</button>
              </span>
            )}
            {selection.week && (
              <span className="inline-flex items-center gap-1 text-xs bg-arctic-mist text-carbon rounded-pill px-3 py-1">
                Week: {selection.week}
                <button onClick={() => select({ week: selection.week })} className="ml-1 hover:text-danger focus-visible:outline-none" aria-label="Remove week filter">✕</button>
              </span>
            )}
            {selection.dayOfWeek && (
              <span className="inline-flex items-center gap-1 text-xs bg-arctic-mist text-carbon rounded-pill px-3 py-1">
                Day: {selection.dayOfWeek}
                <button onClick={() => select({ dayOfWeek: selection.dayOfWeek })} className="ml-1 hover:text-danger focus-visible:outline-none" aria-label="Remove day filter">✕</button>
              </span>
            )}
            <button onClick={clearSelection} className="text-xs text-pewter hover:text-carbon underline-offset-2 hover:underline focus-visible:outline-none">
              Clear all
            </button>
          </div>
        )}

        {/* Breadcrumb */}
        <Breadcrumb
          drillLevel={drillLevel}
          drillClass={drillClass}
          drillStudent={drillStudent}
          entityName={entityName}
          onNavigate={handleBreadcrumb}
        />

        {/* KPI row */}
        {summary && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <KpiCard
              label="Metric rate"
              value={`${summary.metric_rate}%`}
              featured
            />
            <KpiCard
              label="Below threshold"
              value={summary.below_threshold_count.toLocaleString()}
            />
            <KpiCard
              label="Threshold alerts"
              value={String(atRisk.length)}
              sub={loading ? undefined : 'below 75%'}
            />
            <KpiCard
              label="Entities"
              value={summary.entity_count.toLocaleString()}
            />
          </div>
        )}

        {/* Overview: 2×2 chart grid + trends */}
        {drillLevel === 'overview' && (
          <>
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-6">
              <div className="bg-fog border border-arctic-mist rounded-[10px] p-5">
                <p className="text-xs text-pewter uppercase tracking-widest mb-4">Metric rate by group</p>
                <MetricByGroupChart
                  data={classStats}
                  selectedGroup={selection.group}
                  onSelect={handleClassClick}
                  onClassDrill={handleClassDrill}
                  loading={loading}
                />
                <p className="text-xs text-pewter mt-2">Single-click to cross-filter · Double-click to drill down</p>
              </div>

              <div className="bg-fog border border-arctic-mist rounded-[10px] p-5">
                <p className="text-xs text-pewter uppercase tracking-widest mb-4">Weekly trend</p>
                <WeeklyTrendChart
                  data={weeklyStats}
                  loading={loading}
                  selectedWeek={selection.week}
                  onSelect={(week) => select({ week })}
                />
              </div>

              <div className="bg-fog border border-arctic-mist rounded-[10px] p-5">
                <p className="text-xs text-pewter uppercase tracking-widest mb-4">Metric breakdown</p>
                <MetricBreakdownChart
                  data={statusCounts}
                  loading={loading}
                  selectedThreshold={selection.threshold}
                  onSelect={(t) => select({ threshold: t })}
                />
              </div>

              <div className="bg-fog border border-arctic-mist rounded-[10px] p-5">
                <p className="text-xs text-pewter uppercase tracking-widest mb-4">By day of week</p>
                <WeekdayBarChart
                  data={dowStats}
                  loading={loading}
                  selectedDay={selection.dayOfWeek}
                  onSelect={(day) => select({ dayOfWeek: day })}
                />
              </div>
            </div>

            <div className="bg-fog border border-arctic-mist rounded-[10px] p-5 mb-8">
              <p className="text-xs text-pewter uppercase tracking-widest mb-4">30-day vs prior period</p>
              <TrendComparisonChart
                current={trends.current}
                previous={trends.previous}
                loading={loading}
                selectedWeek={selection.week}
                onSelect={(week) => select({ week })}
              />
            </div>
          </>
        )}

        {/* Drill-down panel */}
        <DrilldownPanel
          drillLevel={drillLevel}
          drillClass={drillClass}
          drillStudent={drillStudent}
          atRisk={atRisk}
          sparklines={sparklines}
          loading={loading}
          onInspect={handleInspect}
        />

      </div>

      {panelOpen && (
        <ChatPanel
          atRisk={atRisk}
          summary={summary}
          onClose={() => setPanel(false)}
          onDashboardFilter={handleAgentFilter}
        />
      )}
    </div>
  )
}
