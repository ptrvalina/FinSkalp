import { useEffect } from 'react'

import { cn } from '@/lib/utils'

import type { ComplianceLiveEvent } from '@/hooks/use-compliance-events'

import { subscribeFusionSync, getFusionSyncState } from './fusion-sync-bus'
import type { MioExecutableCard } from './fusion-mio-actions'
import { useIntelligenceStreamPreview } from './useFusionIntelligenceStream'
import { useState } from 'react'

type InboxRow = {
  case_ref?: string
  priority?: string
  workflow_status?: string
  sla_breached?: boolean
}

type Props = {
  liveEvents: ComplianceLiveEvent[]
  mioCards: MioExecutableCard[]
  queueRows?: InboxRow[]
  graphNodeCount?: number
  highestRiskNodeLabel?: string | null
  moneyFlowSummary?: string
  className?: string
}

export function FusionExecutiveBriefing({
  liveEvents,
  mioCards,
  queueRows = [],
  graphNodeCount,
  highestRiskNodeLabel,
  moneyFlowSummary,
  className,
}: Props) {
  const [visible, setVisible] = useState(() => getFusionSyncState().executiveMode)
  const topEvents = useIntelligenceStreamPreview(liveEvents, mioCards, 3)
  const criticalCases = queueRows.filter(
    (r) => r.priority === 'critical' || r.sla_breached
  )
  const topMio = mioCards.find((c) => c.priority === 'critical') ?? mioCards[0]

  useEffect(() => {
    return subscribeFusionSync((sync) => setVisible(sync.executiveMode))
  }, [])

  if (!visible) return null

  return (
    <div
      className={cn(
        'fusion-executive-briefing fixed inset-0 z-[200] flex items-center justify-center bg-[color-mix(in_srgb,var(--fusion-bg-void)_88%,transparent)] p-6',
        className
      )}
      role="dialog"
      aria-modal="true"
      aria-label="Executive briefing"
      data-testid="fusion-executive-briefing"
    >
      <div className="fusion-surface-panel max-h-[90vh] w-full max-w-3xl overflow-auto p-6">
        <header className="mb-4 border-b border-[var(--fusion-border)] pb-3">
          <p className="fusion-text-micro tracking-[0.2em] text-[var(--fusion-ops-yellow)]">
            EXECUTIVE BRIEFING · 30 SEC
          </p>
          <h2 className="fusion-heading-panel mt-1">Operational snapshot</h2>
        </header>

        <section className="mb-4">
          <h3 className="fusion-text-micro mb-2 text-[var(--fusion-text-tertiary)]">
            WHAT HAPPENED
          </h3>
          <ul className="space-y-1">
            {topEvents.length ? (
              topEvents.map((ev) => (
                <li key={ev.id} className="fusion-text-data">
                  · {ev.detail ?? ev.title}
                </li>
              ))
            ) : (
              <li className="fusion-text-micro">No recent stream events</li>
            )}
          </ul>
        </section>

        <section className="mb-4 grid gap-3 sm:grid-cols-2">
          <div className="fusion-surface-deck p-3">
            <h3 className="fusion-text-micro text-[var(--fusion-text-tertiary)]">MAIN RISK</h3>
            <p className="mt-1 fusion-tone-critical fusion-text-data">
              {highestRiskNodeLabel ?? '—'}
            </p>
            {graphNodeCount != null ? (
              <p className="mt-1 fusion-text-micro">{graphNodeCount} entities tracked</p>
            ) : null}
          </div>
          <div className="fusion-surface-deck p-3">
            <h3 className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
              MONEY IN MOTION
            </h3>
            <p className="mt-1 fusion-text-data">{moneyFlowSummary ?? 'Flow overlay active'}</p>
          </div>
        </section>

        <section className="mb-4">
          <h3 className="fusion-text-micro mb-2 text-[var(--fusion-text-tertiary)]">
            CASES NEEDING DECISION
          </h3>
          {criticalCases.length ? (
            <ul className="space-y-1">
              {criticalCases.slice(0, 5).map((row) => (
                <li key={row.case_ref} className="flex justify-between fusion-text-data">
                  <span className="fusion-mono">{row.case_ref}</span>
                  <span className="fusion-text-micro fusion-tone-critical">
                    {row.sla_breached ? 'SLA BREACH' : row.priority}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="fusion-text-micro">No critical queue items</p>
          )}
        </section>

        <section>
          <h3 className="fusion-text-micro mb-2 text-[var(--fusion-text-tertiary)]">
            TOP MIO RECOMMENDATION
          </h3>
          {topMio ? (
            <div className="fusion-surface-deck p-3">
              <p className="fusion-text-data">{topMio.title}</p>
              {topMio.rationale ? (
                <p className="mt-1 fusion-text-micro">{topMio.rationale}</p>
              ) : null}
            </div>
          ) : (
            <p className="fusion-text-micro">No recommendations</p>
          )}
        </section>

        <p className="mt-4 fusion-text-micro text-[var(--fusion-text-tertiary)]">
          Shift+Alt+E or Esc to exit
        </p>
      </div>
    </div>
  )
}
