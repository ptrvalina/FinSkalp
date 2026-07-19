import { useState, type ReactNode } from 'react'

import { cn } from '@/lib/utils'

export type ContextLensId = 'chrono' | 'evidence' | 'entity'

type Props = {
  chrono?: ReactNode
  evidence?: ReactNode
  entity?: ReactNode
  collapsed?: boolean
  onCollapsedChange?: (collapsed: boolean) => void
  eventTicks?: Array<'default' | 'evidence' | 'risk'>
  className?: string
}

const LENSES: Array<{ id: ContextLensId; label: string }> = [
  { id: 'chrono', label: 'Chrono' },
  { id: 'evidence', label: 'Evidence' },
  { id: 'entity', label: 'Entity' },
]

export function FusionContextLens({
  chrono,
  evidence,
  entity,
  collapsed = false,
  onCollapsedChange,
  eventTicks = [],
  className,
}: Props) {
  const [lens, setLens] = useState<ContextLensId>('chrono')

  if (collapsed) {
    return (
      <div className={cn('fusion-canvas-os__context-rail', className)}>
        {eventTicks.slice(0, 12).map((tick, i) => (
          <div
            key={i}
            className={cn(
              'fusion-canvas-os__context-tick',
              tick === 'evidence' && 'fusion-canvas-os__context-tick--evidence',
              tick === 'risk' && 'fusion-canvas-os__context-tick--risk'
            )}
          />
        ))}
        <button
          type="button"
          className="fusion-text-micro mt-auto px-0.5 text-[var(--fusion-ops-blue)]"
          onClick={() => onCollapsedChange?.(false)}
          title="Expand context"
          aria-label="Expand context panel"
        >
          ›
        </button>
      </div>
    )
  }

  const body =
    lens === 'chrono' ? chrono : lens === 'evidence' ? evidence : entity

  return (
    <div className={cn('fusion-canvas-os__context flex flex-col', className)}>
      <div className="flex items-center border-b border-[var(--fusion-border)]">
        <div className="fusion-context-lens__tabs flex-1">
          {LENSES.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={cn(
                'fusion-context-lens__tab',
                lens === tab.id && 'fusion-context-lens__tab--active'
              )}
              onClick={() => setLens(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <button
          type="button"
          className="fusion-text-micro shrink-0 px-2 py-1 text-[var(--fusion-text-tertiary)] hover:text-[var(--fusion-ops-blue)]"
          onClick={() => onCollapsedChange?.(true)}
          title="Collapse context"
          aria-label="Collapse context panel"
        >
          ‹
        </button>
      </div>
      <div className="fusion-context-lens__body">{body}</div>
    </div>
  )
}
