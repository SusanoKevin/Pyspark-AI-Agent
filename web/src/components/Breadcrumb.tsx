import { DrillLevel } from '../types'

interface Props {
  drillLevel:   DrillLevel
  drillClass:   string | null
  drillStudent: number | null
  entityName?:  string
  onNavigate:   (level: DrillLevel) => void
}

export default function Breadcrumb({ drillLevel, drillClass, drillStudent, entityName, onNavigate }: Props) {
  if (drillLevel === 'overview') return null

  return (
    <nav aria-label="Drill-down breadcrumb" className="flex items-center gap-1.5 text-sm text-pewter mb-6">
      <button
        onClick={() => onNavigate('overview')}
        className="hover:text-carbon transition-colors rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-link-blue focus-visible:ring-offset-1"
      >
        Overview
      </button>

      {drillClass && (
        <>
          <span aria-hidden="true" className="text-arctic-mist select-none">›</span>
          {drillLevel === 'group' ? (
            <span className="text-carbon font-medium">{drillClass}</span>
          ) : (
            <button
              onClick={() => onNavigate('group')}
              className="hover:text-carbon transition-colors rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-link-blue focus-visible:ring-offset-1"
            >
              {drillClass}
            </button>
          )}
        </>
      )}

      {drillLevel === 'entity' && drillStudent !== null && (
        <>
          <span aria-hidden="true" className="text-arctic-mist select-none">›</span>
          <span className="text-carbon font-medium">{entityName ?? `Entity #${drillStudent}`}</span>
        </>
      )}
    </nav>
  )
}
