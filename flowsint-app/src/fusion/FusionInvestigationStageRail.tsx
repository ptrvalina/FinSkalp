import { cn } from '@/lib/utils'

import type { InvestigationPhaseSnapshot } from './fusion-investigation-phase'

type Props = {
  phase: InvestigationPhaseSnapshot
  busy?: boolean
  onNext?: () => void
  className?: string
}

/** Horizontal stage rail: where am I / what next — operator clarity. */
export function FusionInvestigationStageRail({ phase, busy, onNext, className }: Props) {
  const showCta = phase.nextActionKind !== 'wait' && phase.nextActionKind !== 'none' && onNext

  return (
    <div
      className={cn('fusion-stage-rail', phase.finished && 'fusion-stage-rail--done', className)}
      data-testid="fusion-stage-rail"
      data-stage={phase.currentId}
    >
      <div className="fusion-stage-rail__now">
        <span className="fusion-stage-rail__now-label">{phase.nowLabel}</span>
        <span className="fusion-stage-rail__pct">{phase.progressPct}%</span>
      </div>
      <ol className="fusion-stage-rail__steps" aria-label="Этапы расследования">
        {phase.stages.map((step) => (
          <li
            key={step.id}
            className={cn(
              'fusion-stage-rail__step',
              step.status === 'done' && 'fusion-stage-rail__step--done',
              step.status === 'current' && 'fusion-stage-rail__step--current',
              step.status === 'todo' && 'fusion-stage-rail__step--todo'
            )}
          >
            <span className="fusion-stage-rail__dot" aria-hidden>
              {step.status === 'done' ? '✓' : step.index}
            </span>
            <span className="fusion-stage-rail__step-label">{step.label}</span>
          </li>
        ))}
      </ol>
      {showCta ? (
        <button
          type="button"
          className="fusion-stage-rail__cta"
          disabled={busy}
          onClick={onNext}
        >
          {busy ? '…' : `Сейчас → ${phase.nextActionLabel}`}
        </button>
      ) : phase.nextActionKind === 'wait' ? (
        <span className="fusion-stage-rail__wait">{phase.nextActionLabel}</span>
      ) : null}
    </div>
  )
}
