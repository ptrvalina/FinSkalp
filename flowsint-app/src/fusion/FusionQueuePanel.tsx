import { memo, useMemo, useState } from 'react'

import { Link } from '@tanstack/react-router'

import { cn } from '@/lib/utils'

import { FusionEmptyState } from './FusionEmptyState'
import { fusionChildSearch } from './fusion-route-search'
import { fusionCopy } from './fusion-copy'

export type FusionQueueRow = {
  case_id: string
  case_ref?: string | null
  title_ru?: string | null
  priority?: string | null
  workflow_status?: string | null
  assignee_name?: string | null
  sla_breached?: boolean
  queue_priority?: number | null
}

export type QueueStatusFilter = 'all' | 'new' | 'triage' | 'investigating' | 'pending_filing' | 'critical'

type Props = {
  rows: FusionQueueRow[]
  activeCaseRef?: string | null
  onStartCollect?: () => void
  /** Mission Control: click row to preview graph without leaving queue */
  onSelectPreview?: (row: FusionQueueRow) => void
  onTriage?: (row: FusionQueueRow) => void
  onDefer?: (row: FusionQueueRow) => void
  triageBusyId?: string | null
  className?: string
}

function isCriticalRow(row: FusionQueueRow): boolean {
  return row.priority?.toLowerCase() === 'critical' || Boolean(row.sla_breached)
}

const FILTERS: Array<{ id: QueueStatusFilter; label: string }> = [
  { id: 'all', label: fusionCopy.queue.filterAll },
  { id: 'critical', label: fusionCopy.queue.filterCritical },
  { id: 'new', label: fusionCopy.queue.filterNew },
  { id: 'triage', label: fusionCopy.queue.filterTriage },
  { id: 'investigating', label: fusionCopy.queue.filterInvestigating },
  { id: 'pending_filing', label: fusionCopy.queue.filterFiling },
]

/** Persistent Mission Control queue — not an overlay lens. */
export const FusionQueuePanel = memo(function FusionQueuePanel({
  rows,
  activeCaseRef,
  onStartCollect,
  onSelectPreview,
  onTriage,
  onDefer,
  triageBusyId,
  className,
}: Props) {
  const [filter, setFilter] = useState<QueueStatusFilter>('all')

  const filtered = useMemo(() => {
    if (filter === 'all') return rows
    if (filter === 'critical') return rows.filter(isCriticalRow)
    return rows.filter((r) => (r.workflow_status ?? '').toLowerCase() === filter)
  }, [rows, filter])

  return (
    <div className={cn('fusion-queue-panel flex h-full min-h-0 flex-col', className)} data-testid="fusion-queue-panel">
      <div className="border-b border-[var(--fusion-border)] px-3 py-2">
        <p className="fusion-heading-panel text-[11px] normal-case">{fusionCopy.queue.title}</p>
        <p className="fusion-text-micro mt-0.5 text-[var(--fusion-text-tertiary)]">
          {fusionCopy.queue.subtitle(filtered.length)}
        </p>
        <div className="mt-2 flex flex-wrap gap-1">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              className={cn(
                'fusion-text-micro rounded border px-1.5 py-0.5',
                filter === f.id
                  ? 'border-[var(--fusion-ops-blue)] text-[var(--fusion-ops-blue)]'
                  : 'border-[var(--fusion-border)] text-[var(--fusion-text-tertiary)]'
              )}
              onClick={() => setFilter(f.id)}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        {filtered.length === 0 ? (
          <FusionEmptyState
            className="py-6"
            title={fusionCopy.queue.emptyTitle}
            description={fusionCopy.queue.emptyDescription}
            action={
              onStartCollect ? (
                <button
                  type="button"
                  className="fusion-text-micro rounded border border-[var(--fusion-border)] px-3 py-1.5 text-[var(--fusion-ops-blue)]"
                  onClick={onStartCollect}
                >
                  {fusionCopy.queue.collectSeed}
                </button>
              ) : null
            }
          />
        ) : (
          <ul className="divide-y divide-[var(--fusion-border)]">
            {filtered.map((row) => {
              const ref = row.case_ref ?? row.case_id
              const isActive = activeCaseRef != null && ref === activeCaseRef
              const isCritical = isCriticalRow(row)
              const busy = triageBusyId === row.case_id
              return (
                <li
                  key={row.case_id}
                  data-queue-row
                  data-active={isActive ? 'true' : undefined}
                  className={cn(isCritical && !isActive && 'fusion-queue-panel__row--critical')}
                >
                  <div
                    className={cn(
                      'px-3 py-2 fusion-text-data',
                      isActive && 'bg-[color-mix(in_srgb,var(--fusion-ops-blue)_10%,transparent)]'
                    )}
                  >
                    {onSelectPreview ? (
                      <button
                        type="button"
                        className="block w-full text-left hover:opacity-90"
                        onClick={() => onSelectPreview(row)}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="fusion-mono fusion-tone-ops fusion-truncate">{ref}</span>
                          <span className="flex shrink-0 items-center gap-1">
                            {row.sla_breached ? (
                              <span className="fusion-text-micro rounded border border-[var(--fusion-ops-red)] px-1 text-[var(--fusion-ops-red)]">
                                {fusionCopy.queue.slaBreach}
                              </span>
                            ) : null}
                            {row.priority?.toLowerCase() === 'critical' ? (
                              <span className="fusion-text-micro fusion-tone-critical">
                                {fusionCopy.mio.priority.critical}
                              </span>
                            ) : null}
                            <span className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
                              {row.workflow_status ?? '—'}
                            </span>
                          </span>
                        </div>
                        <p className="fusion-text-micro mt-0.5 fusion-truncate text-[var(--fusion-text-tertiary)]">
                          {row.title_ru ?? row.assignee_name ?? '—'}
                        </p>
                      </button>
                    ) : (
                      <Link
                        to="/dashboard/fusion/investigation/$caseRef"
                        params={{ caseRef: ref }}
                        search={fusionChildSearch()}
                        className="block hover:opacity-90"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="fusion-mono fusion-tone-ops fusion-truncate">{ref}</span>
                          <span className="flex shrink-0 items-center gap-1">
                            {row.sla_breached ? (
                              <span className="fusion-text-micro rounded border border-[var(--fusion-ops-red)] px-1 text-[var(--fusion-ops-red)]">
                                {fusionCopy.queue.slaBreach}
                              </span>
                            ) : null}
                            {row.priority?.toLowerCase() === 'critical' ? (
                              <span className="fusion-text-micro fusion-tone-critical">
                                {fusionCopy.mio.priority.critical}
                              </span>
                            ) : null}
                            <span className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
                              {row.workflow_status ?? '—'}
                            </span>
                          </span>
                        </div>
                        <p className="fusion-text-micro mt-0.5 fusion-truncate text-[var(--fusion-text-tertiary)]">
                          {row.title_ru ?? row.assignee_name ?? '—'}
                        </p>
                      </Link>
                    )}
                    {onSelectPreview ? (
                      <Link
                        to="/dashboard/fusion/investigation/$caseRef"
                        params={{ caseRef: ref }}
                        search={fusionChildSearch()}
                        className="fusion-text-micro mt-1 inline-block text-[var(--fusion-ops-blue)] hover:underline"
                      >
                        {fusionCopy.queue.linkInvestigation}
                      </Link>
                    ) : null}
                    {(onTriage || onDefer) && (
                      <div className="mt-1.5 flex gap-1">
                        {onTriage ? (
                          <button
                            type="button"
                            disabled={busy}
                            className="fusion-text-micro rounded border border-[var(--fusion-border)] px-1.5 py-0.5 text-[var(--fusion-ops-blue)] disabled:opacity-50"
                            onClick={() => onTriage(row)}
                          >
                            {fusionCopy.queue.triage}
                          </button>
                        ) : null}
                        {onDefer ? (
                          <button
                            type="button"
                            disabled={busy}
                            className="fusion-text-micro rounded border border-[var(--fusion-border)] px-1.5 py-0.5 text-[var(--fusion-text-tertiary)] disabled:opacity-50"
                            onClick={() => onDefer(row)}
                          >
                            {fusionCopy.queue.defer}
                          </button>
                        ) : null}
                      </div>
                    )}
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
})
