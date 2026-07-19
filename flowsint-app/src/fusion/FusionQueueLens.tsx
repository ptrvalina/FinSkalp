import { Link } from '@tanstack/react-router'

import { cn } from '@/lib/utils'

type QueueRow = {
  case_id: string
  case_ref?: string | null
  title_ru?: string | null
  priority?: string | null
  workflow_status?: string | null
  assignee_name?: string | null
}

type Props = {
  open: boolean
  onClose: () => void
  rows: QueueRow[]
  className?: string
}

export function FusionQueueLens({ open, onClose, rows, className }: Props) {
  if (!open) return null

  return (
    <>
      <button
        type="button"
        className="fusion-seed-lens__backdrop"
        aria-label="Close queue"
        onClick={onClose}
      />
      <div className={cn('fusion-queue-lens', className)} data-testid="fusion-queue-lens">
        <div className="fusion-queue-lens__header">
          <span className="fusion-heading-panel text-[11px] normal-case">Case Queue · Lens</span>
          <button type="button" className="fusion-text-micro text-[var(--fusion-ops-blue)]" onClick={onClose}>
            Close ✕
          </button>
        </div>
        <ul className="fusion-queue-lens__list divide-y divide-[var(--fusion-border)]">
          {rows.length === 0 ? (
            <li className="fusion-text-micro p-6 text-center text-[var(--fusion-text-tertiary)]">
              Queue empty — start investigation via ⌘K or Collect
            </li>
          ) : (
            rows.map((row) => (
              <li key={row.case_id} className="px-3 py-2 hover:bg-[var(--fusion-bg-panel)]">
                <Link
                  to="/dashboard/fusion/investigation/$caseRef"
                  params={{ caseRef: row.case_ref ?? row.case_id }}
                  className="block fusion-text-data"
                  onClick={onClose}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="fusion-mono fusion-tone-ops">{row.case_ref ?? '—'}</span>
                    <span className="fusion-text-micro">{row.workflow_status ?? row.priority ?? ''}</span>
                  </div>
                  <p className="fusion-text-micro mt-0.5 fusion-truncate text-[var(--fusion-text-tertiary)]">
                    {row.title_ru ?? row.assignee_name ?? '—'}
                  </p>
                </Link>
              </li>
            ))
          )}
        </ul>
      </div>
    </>
  )
}
