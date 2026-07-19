import { FusionInvestigationLauncher } from './FusionInvestigationLauncher'
import type { StartInvestigationParams } from './fusion-investigation-start'

type Props = {
  open: boolean
  onClose: () => void
  onSubmit: (params: StartInvestigationParams) => void
  isSubmitting?: boolean
}

export function FusionSeedLensOverlay({ open, onClose, onSubmit, isSubmitting }: Props) {
  if (!open) return null

  return (
    <>
      <button
        type="button"
        className="fusion-seed-lens__backdrop"
        aria-label="Close seed lens"
        onClick={onClose}
      />
      <div className="fusion-seed-lens" data-testid="fusion-seed-lens">
        <div className="flex items-center justify-between border-b border-[var(--fusion-border)] px-3 py-2">
          <span className="fusion-heading-panel text-[11px] normal-case">Seed Ingress · ⌘K</span>
          <button type="button" className="fusion-text-micro text-[var(--fusion-ops-blue)]" onClick={onClose}>
            ✕
          </button>
        </div>
        <FusionInvestigationLauncher
          className="border-0"
          onSubmit={onSubmit}
          isSubmitting={isSubmitting}
        />
      </div>
    </>
  )
}
