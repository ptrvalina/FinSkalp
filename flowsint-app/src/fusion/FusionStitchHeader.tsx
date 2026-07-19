import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

type Props = {
  caseRef?: string | null
  sessionLabel?: string
  /** Human-readable phase: e.g. "В ПРОЦЕССЕ · 15 узлов · fusion не запущен" */
  phaseLabel?: string | null
  phaseTone?: 'idle' | 'active' | 'done' | 'error'
  live?: boolean
  onRunCollection?: () => void
  runDisabled?: boolean
  runLabel?: string
  actions?: ReactNode
  className?: string
}

/** Graph OS command strip (48px). */
export function FusionStitchHeader({
  caseRef,
  sessionLabel,
  phaseLabel,
  phaseTone = 'active',
  live = true,
  onRunCollection,
  runDisabled,
  runLabel = 'Run Collection',
  actions,
  className,
}: Props) {
  return (
    <header className={cn('fusion-stitch-header', className)} data-testid="fusion-stitch-header">
      <div className="fusion-stitch-header__left">
        {caseRef ? (
          <>
            <span className="fusion-stitch-header__case">{caseRef}</span>
            {sessionLabel ? (
              <>
                <span className="text-[var(--fusion-border)]">|</span>
                <span>{sessionLabel}</span>
              </>
            ) : null}
          </>
        ) : (
          <span className="fusion-stitch-header__case">MISSION CONTROL</span>
        )}
        <span className="text-[var(--fusion-border)]">|</span>
        <span className="fusion-stitch-header__live">
          {live ? (
            <>
              <span className="fusion-stitch-header__live-dot" aria-hidden />
              ACTIVE SESSION
            </>
          ) : (
            'PAUSED'
          )}
        </span>
        {phaseLabel ? (
          <>
            <span className="text-[var(--fusion-border)]">|</span>
            <span
              className={cn(
                'fusion-stitch-header__phase',
                phaseTone === 'done' && 'fusion-stitch-header__phase--done',
                phaseTone === 'error' && 'fusion-stitch-header__phase--error',
                phaseTone === 'idle' && 'fusion-stitch-header__phase--idle'
              )}
              data-testid="fusion-phase-badge"
            >
              {phaseLabel}
            </span>
          </>
        ) : null}
      </div>
      <div className="fusion-stitch-header__actions">
        {actions}
        {onRunCollection ? (
          <button
            type="button"
            className="fusion-stitch-header__run"
            onClick={onRunCollection}
            disabled={runDisabled}
          >
            {runLabel}
          </button>
        ) : null}
      </div>
    </header>
  )
}
