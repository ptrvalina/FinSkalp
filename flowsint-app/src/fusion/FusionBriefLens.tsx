import type { ComplianceLiveEvent } from '@/hooks/use-compliance-events'

import { cn } from '@/lib/utils'

import { FusionExecutiveBriefing } from './FusionExecutiveBriefing'
import { fusionCopy } from './fusion-copy'
import type { MioExecutableCard } from './fusion-mio-actions'

type Props = {
  open: boolean
  onClose: () => void
  liveEvents: ComplianceLiveEvent[]
  mioCards: MioExecutableCard[]
  graphNodeCount?: number
  highestRiskNodeLabel?: string | null
  moneyFlowSummary?: string
  className?: string
}

export function FusionBriefLens({
  open,
  onClose,
  liveEvents,
  mioCards,
  graphNodeCount,
  highestRiskNodeLabel,
  moneyFlowSummary,
  className,
}: Props) {
  if (!open) return null

  return (
    <>
      <button
        type="button"
        className="fusion-seed-lens__backdrop fusion-seed-lens__backdrop--graph-os"
        style={{ left: 56 }}
        aria-label={fusionCopy.brief.ariaLabel}
        onClick={onClose}
      />
      <div className={cn('fusion-brief-lens', className)} data-testid="fusion-brief-lens">
        <div className="flex items-center justify-between border-b border-[var(--fusion-border)] px-3 py-2">
          <span className="fusion-heading-panel text-[11px] normal-case">{fusionCopy.brief.header}</span>
          <button type="button" className="fusion-text-micro text-[var(--fusion-ops-blue)]" onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="relative max-h-[70vh] overflow-auto p-2">
          <FusionExecutiveBriefing
            liveEvents={liveEvents}
            mioCards={mioCards}
            graphNodeCount={graphNodeCount}
            highestRiskNodeLabel={highestRiskNodeLabel}
            moneyFlowSummary={moneyFlowSummary}
            className="!static !inset-auto !z-auto !flex !bg-transparent !p-0"
          />
        </div>
      </div>
    </>
  )
}
