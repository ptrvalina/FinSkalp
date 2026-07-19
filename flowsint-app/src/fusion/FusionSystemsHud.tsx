import { cn } from '@/lib/utils'

type Props = {
  scalpelLive?: boolean
  nodeCount?: number
  riskLogicOk?: boolean
  className?: string
}

export function FusionSystemsHud({
  scalpelLive = false,
  nodeCount = 0,
  riskLogicOk = true,
  className,
}: Props) {
  return (
    <div
      className={cn('fusion-systems-hud', className)}
      data-testid="fusion-systems-hud"
      aria-label="Systems status"
    >
      <div className="fusion-systems-hud__row">
        <span
          className={cn(
            'fusion-systems-hud__dot',
            scalpelLive ? 'fusion-systems-hud__dot--live' : 'bg-[var(--fusion-text-tertiary)]'
          )}
          aria-hidden
        />
        <span>Scalpel {scalpelLive ? 'LIVE' : 'IDLE'}</span>
      </div>
      <div className="fusion-systems-hud__row">
        <span className="fusion-systems-hud__dot bg-[var(--fusion-ops-blue)]" aria-hidden />
        <span>Visualizer {nodeCount} nodes</span>
      </div>
      <div className="fusion-systems-hud__row">
        <span
          className={cn(
            'fusion-systems-hud__dot',
            riskLogicOk ? 'fusion-systems-hud__dot--live' : 'fusion-systems-hud__dot--error'
          )}
          aria-hidden
        />
        <span>Risk Logic {riskLogicOk ? 'OK' : 'ERROR'}</span>
      </div>
    </div>
  )
}
