import { Progress } from '@/components/ui/progress'

export type ConfidenceDimensions = {
  identity_confidence: number
  evidence_strength: number
  relationship_confidence: number
  source_reliability: number
  aggregate_risk_score: number
  explain_ru?: Record<string, string>
}

type Props = {
  dimensions: ConfidenceDimensions
  compact?: boolean
}

const AXES: Array<{ key: keyof ConfidenceDimensions; label: string }> = [
  { key: 'identity_confidence', label: 'Идентификация' },
  { key: 'evidence_strength', label: 'Доказательства' },
  { key: 'relationship_confidence', label: 'Связи' },
  { key: 'source_reliability', label: 'Источники' },
]

export function ConfidenceBreakdownPanel({ dimensions, compact }: Props) {
  return (
    <div className="space-y-3">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-sm font-medium">Risk Score</span>
        <button
          type="button"
          className="font-mono text-2xl text-[var(--fusion-ops-blue)] hover:underline"
          title="Интегральный индекс — раскройте оси confidence ниже"
        >
          {dimensions.aggregate_risk_score.toFixed(0)}
        </button>
      </div>
      {!compact ? (
        <ul className="space-y-2">
          {AXES.map(({ key, label }) => {
            const value = Number(dimensions[key] ?? 0)
            return (
              <li key={key} className="space-y-1">
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>{label}</span>
                  <span>{(value * 100).toFixed(0)}%</span>
                </div>
                <Progress value={value * 100} className="h-1.5" />
              </li>
            )
          })}
        </ul>
      ) : null}
      {dimensions.explain_ru?.formula_ru ? (
        <p className="text-xs text-muted-foreground">{dimensions.explain_ru.formula_ru}</p>
      ) : null}
    </div>
  )
}
