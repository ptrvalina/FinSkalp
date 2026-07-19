import { cn } from '@/lib/utils'

import { WORKFLOW_LABELS } from './fusion-mission-data'
import { loadCaseSession } from './fusion-case-session'

type Props = {
  caseRef: string
  workflowStatus?: string | null
  riskScore?: number | string | null
  riskLevel?: string | null
  priority?: string | null
  className?: string
}

function formatLastAction(caseRef: string): string {
  const session = loadCaseSession(caseRef)
  if (!session.lastAction) return '—'
  const ago =
    session.lastActionAt != null
      ? `${Math.max(0, Math.round((Date.now() - session.lastActionAt) / 60_000))}m`
      : ''
  return ago ? `${session.lastAction} · ${ago}` : session.lastAction
}

export function FusionInvestigationContextBar({
  caseRef,
  workflowStatus,
  riskScore,
  riskLevel,
  priority,
  className,
}: Props) {
  const workflowLabel =
    (workflowStatus && WORKFLOW_LABELS[workflowStatus]) ??
    workflowStatus?.replace(/_/g, ' ').toUpperCase() ??
    '—'

  const risk =
    riskScore != null && riskScore !== ''
      ? `${riskScore}${riskLevel ? ` · ${riskLevel}` : ''}`
      : riskLevel ?? '—'

  return (
    <div
      className={cn(
        'fusion-inv-context-bar flex flex-wrap items-center gap-x-3 gap-y-0.5 border-b border-[var(--fusion-border)] bg-[var(--fusion-bg-panel)] px-3 py-1',
        className
      )}
      data-testid="fusion-inv-context-bar"
    >
      <span className="fusion-mono fusion-text-micro text-[var(--fusion-ops-blue)]">{caseRef}</span>
      <span className="fusion-text-micro text-[var(--fusion-text-tertiary)]">|</span>
      <span className="fusion-text-micro">
        <span className="text-[var(--fusion-text-tertiary)]">WF </span>
        {workflowLabel}
      </span>
      {priority ? (
        <>
          <span className="fusion-text-micro text-[var(--fusion-text-tertiary)]">|</span>
          <span className="fusion-text-micro fusion-tone-warning uppercase">{priority}</span>
        </>
      ) : null}
      <span className="fusion-text-micro text-[var(--fusion-text-tertiary)]">|</span>
      <span className="fusion-text-micro">
        <span className="text-[var(--fusion-text-tertiary)]">RISK </span>
        <span className="fusion-tone-critical">{risk}</span>
      </span>
      <span className="fusion-text-micro text-[var(--fusion-text-tertiary)]">|</span>
      <span className="fusion-text-micro min-w-0 flex-1 fusion-truncate">
        <span className="text-[var(--fusion-text-tertiary)]">LAST </span>
        {formatLastAction(caseRef)}
      </span>
    </div>
  )
}
