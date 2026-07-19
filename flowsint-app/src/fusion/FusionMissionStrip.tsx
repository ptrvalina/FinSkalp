import { cn } from '@/lib/utils'

export type FusionMissionStripData = {
  objective?: string
  threat?: string
  status?: string
  intelligence?: string
  hypotheses?: string | number
  evidenceQuality?: string | number
  confidence?: string | number
  entities?: string | number
  wallets?: string | number
  txVelocity?: string
  riskEvolution?: string
  timeline?: string | number
  recommendations?: string | number
  queue?: string | number
}

type Tone = 'default' | 'critical' | 'warning' | 'caution' | 'clear' | 'ops'

type CellDef = {
  key: keyof FusionMissionStripData
  label: string
  tone?: Tone
}

const CELLS: CellDef[] = [
  { key: 'objective', label: 'Objective', tone: 'ops' },
  { key: 'threat', label: 'Threat', tone: 'warning' },
  { key: 'status', label: 'Status', tone: 'ops' },
  { key: 'intelligence', label: 'Intelligence' },
  { key: 'hypotheses', label: 'Hypotheses' },
  { key: 'evidenceQuality', label: 'Evidence Q' },
  { key: 'confidence', label: 'Confidence', tone: 'clear' },
  { key: 'entities', label: 'Entities' },
  { key: 'wallets', label: 'Wallets' },
  { key: 'txVelocity', label: 'Tx Velocity' },
  { key: 'riskEvolution', label: 'Risk Evol' },
  { key: 'timeline', label: 'Timeline' },
  { key: 'recommendations', label: 'Recs' },
  { key: 'queue', label: 'Queue' },
]

function formatValue(value: string | number | undefined): string {
  if (value === undefined || value === null || value === '') return '—'
  return String(value)
}

export function FusionMissionStrip({ data }: { data: FusionMissionStripData }) {
  return (
    <div className="fusion-mission-strip" data-testid="fusion-mission-strip">
      {CELLS.map((cell) => {
        const value = formatValue(data[cell.key])
        return (
          <div key={cell.key} className="fusion-mission-strip__cell">
            <p className="fusion-mission-strip__label">{cell.label}</p>
            <p
              className={cn(
                'fusion-mission-strip__value',
                cell.tone === 'critical' && 'fusion-mission-strip__value--critical',
                cell.tone === 'warning' && 'fusion-mission-strip__value--warning',
                cell.tone === 'caution' && 'fusion-mission-strip__value--caution',
                cell.tone === 'clear' && 'fusion-mission-strip__value--clear',
                cell.tone === 'ops' && 'fusion-mission-strip__value--ops'
              )}
            >
              {value}
            </p>
          </div>
        )
      })}
    </div>
  )
}
