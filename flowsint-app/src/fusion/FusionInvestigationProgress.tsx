import { cn } from '@/lib/utils'

import { fusionCopy } from './fusion-copy'

type Props = {
  phase?: 'collectors' | 'graph' | 'kyt' | 'done' | null
  active?: boolean
  error?: boolean
  errorMessage?: string | null
  collectorStatus?: Record<string, string>
  collectorsRun?: string[]
  onRetry?: () => void
  className?: string
}

const PHASE_LABEL: Record<NonNullable<Props['phase']>, string> = {
  collectors: fusionCopy.investigation.pipelineCollectors,
  graph: fusionCopy.investigation.pipelineGraph,
  kyt: fusionCopy.investigation.pipelineKyt,
  done: fusionCopy.investigation.pipelineDone,
}

export function FusionInvestigationProgress({
  phase,
  active,
  error,
  errorMessage,
  collectorStatus,
  collectorsRun,
  onRetry,
  className,
}: Props) {
  if (error) {
    const failed = Object.entries(collectorStatus ?? {})
      .filter(([, status]) => String(status).toLowerCase().startsWith('error'))
      .map(([id]) => id)
    return (
      <div
        className={cn('fusion-investigation-progress fusion-investigation-progress--error', className)}
        data-testid="fusion-investigation-progress"
        role="alert"
      >
        <span className="fusion-text-micro">{errorMessage || fusionCopy.investigation.pipelineError}</span>
        {failed.length ? (
          <span className="fusion-text-micro text-[var(--fusion-ops-amber)]">
            {fusionCopy.investigation.pipelineFailedCollectors(failed.length)}: {failed.join(', ')}
          </span>
        ) : null}
        {onRetry ? (
          <button
            type="button"
            className="fusion-text-micro rounded border border-[var(--fusion-ops-blue)] px-2 py-0.5 text-[var(--fusion-ops-blue)]"
            onClick={onRetry}
          >
            {fusionCopy.investigation.pipelineRetry}
          </button>
        ) : null}
      </div>
    )
  }

  if (!active || !phase || phase === 'done') return null

  const chips = collectorsRun?.length
    ? collectorsRun
    : Object.keys(collectorStatus ?? {})

  return (
    <div
      className={cn('fusion-investigation-progress', className)}
      data-testid="fusion-investigation-progress"
      role="status"
      aria-live="polite"
    >
      <span className="fusion-investigation-progress__pulse" aria-hidden />
      <span className="fusion-text-micro">{PHASE_LABEL[phase]}</span>
      {phase === 'collectors' && chips.length ? (
        <div className="flex flex-wrap gap-1">
          {chips.map((id) => {
            const status = collectorStatus?.[id] ?? 'pending'
            const ok = String(status).toLowerCase() === 'ok'
            const bad = String(status).toLowerCase().startsWith('error')
            return (
              <span
                key={id}
                className={cn(
                  'fusion-text-micro rounded border px-1.5 py-0.5',
                  ok && 'border-[var(--fusion-ops-blue)] text-[var(--fusion-ops-blue)]',
                  bad && 'border-[var(--fusion-ops-red)] text-[var(--fusion-ops-red)]',
                  !ok && !bad && 'border-[var(--fusion-border)] text-[var(--fusion-text-tertiary)]'
                )}
                title={status}
              >
                {id}
              </span>
            )
          })}
        </div>
      ) : null}
    </div>
  )
}
