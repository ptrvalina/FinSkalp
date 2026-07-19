import { cn } from '@/lib/utils'

import { FusionInlineError } from './FusionInlineError'
import type { MIOActionCard } from './FusionMIO'
import type { MioContradiction } from './fusion-mio-heuristics'

export type MioBriefingContext = {
  caseRef?: string
  priority?: string
  openAlertsCount?: number
  workflowStatus?: string
}

const PRIORITY_CLASS: Record<string, string> = {
  critical: 'fusion-tone-critical',
  high: 'fusion-tone-warning',
  medium: 'fusion-tone-caution',
  low: 'fusion-tone-ops',
}

type Props = {
  context: MioBriefingContext
  topCards: MIOActionCard[]
  pinnedCritical?: MIOActionCard | null
  contradictions?: MioContradiction[]
  selectedCount: number
  totalCards: number
  canExecute: boolean
  batchRunning: boolean
  batchProgress?: { current: number; total: number }
  dependencyHint?: string | null
  batchSummaryError?: string | null
  lastRefreshedAt?: Date
  isRefreshing?: boolean
  onExecuteAll: () => void
  onSelectAll: () => void
}

function formatRefreshTime(date?: Date): string {
  if (!date) return '—'
  return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export function FusionMioBriefingStrip({
  context,
  topCards,
  pinnedCritical,
  contradictions = [],
  selectedCount,
  totalCards,
  canExecute,
  batchRunning,
  batchProgress,
  dependencyHint,
  batchSummaryError,
  lastRefreshedAt,
  isRefreshing,
  onExecuteAll,
  onSelectAll,
}: Props) {
  const allSelected = totalCards > 0 && selectedCount === totalCards

  return (
    <div
      className="fusion-mio-briefing border-b border-[var(--fusion-border)] bg-[var(--fusion-bg-panel)] px-2 py-1.5"
      data-testid="fusion-mio-briefing"
    >
      <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
        {context.caseRef ? (
          <span className="fusion-mono fusion-text-micro text-[var(--fusion-ops-blue)]">
            {context.caseRef}
          </span>
        ) : null}
        {context.priority ? (
          <span
            className={cn(
              'fusion-text-micro uppercase',
              PRIORITY_CLASS[context.priority.toLowerCase()] ?? 'fusion-tone-ops'
            )}
          >
            {context.priority}
          </span>
        ) : null}
        {context.workflowStatus ? (
          <span className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
            {context.workflowStatus.replace(/_/g, ' ').toUpperCase()}
          </span>
        ) : null}
        {context.openAlertsCount != null && context.openAlertsCount > 0 ? (
          <span className="fusion-text-micro fusion-tone-critical">
            {context.openAlertsCount} ALERT{context.openAlertsCount === 1 ? '' : 'S'}
          </span>
        ) : null}
        <span className="ml-auto fusion-text-micro text-[var(--fusion-text-tertiary)]">
          {isRefreshing ? 'SYNC…' : formatRefreshTime(lastRefreshedAt)}
        </span>
      </div>

      {pinnedCritical ? (
        <div className="mt-1 rounded-sm border border-[var(--fusion-ops-red)]/40 bg-[var(--fusion-bg-deck)] px-2 py-1">
          <span className="fusion-text-micro fusion-tone-critical">PIN · CRITICAL</span>
          <p className="fusion-text-micro fusion-truncate" title={pinnedCritical.title}>
            {pinnedCritical.title}
          </p>
        </div>
      ) : null}

      {contradictions.length > 0 ? (
        <p className="mt-1 fusion-text-micro fusion-tone-warning">
          {contradictions[0]!.reason}
        </p>
      ) : null}

      {topCards.length > 0 ? (
        <ul className="mt-1 space-y-0.5">
          {topCards.map((card, index) => (
            <li key={card.id} className="flex min-w-0 items-start gap-1">
              <span className="fusion-text-micro shrink-0 text-[var(--fusion-text-tertiary)]">
                {index + 1}.
              </span>
              <span className="fusion-text-micro fusion-truncate" title={card.title}>
                {card.title}
              </span>
            </li>
          ))}
        </ul>
      ) : null}

      <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
        {canExecute && totalCards > 0 ? (
          <button
            type="button"
            className="px-1.5 py-0.5 fusion-text-micro border border-[var(--fusion-border)] rounded-[var(--fusion-radius-sm)] text-[var(--fusion-text-tertiary)] hover:text-[var(--fusion-text-secondary)]"
            onClick={onSelectAll}
            disabled={batchRunning}
          >
            {allSelected ? 'DESELECT' : 'SELECT ALL'}
          </button>
        ) : null}
        {dependencyHint ? (
          <span className="fusion-text-micro text-[var(--fusion-ops-yellow)]">{dependencyHint}</span>
        ) : null}
        <button
          type="button"
          className={cn(
            'ml-auto px-2 py-0.5 fusion-text-micro border rounded-[var(--fusion-radius-sm)]',
            canExecute && selectedCount > 0 && !batchRunning
              ? 'border-[var(--fusion-ops-blue)] text-[var(--fusion-ops-blue)]'
              : 'border-[var(--fusion-border)] text-[var(--fusion-text-tertiary)]'
          )}
          onClick={onExecuteAll}
          disabled={!canExecute || batchRunning || selectedCount === 0}
          title={!canExecute ? 'Read-only role' : undefined}
        >
          {batchRunning && batchProgress
            ? `EXEC ${batchProgress.current}/${batchProgress.total}`
            : `EXEC ALL (${selectedCount})`}
        </button>
      </div>
      {batchSummaryError ? (
        <FusionInlineError message={batchSummaryError} className="mt-1.5" />
      ) : null}
    </div>
  )
}
