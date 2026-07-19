import { useCallback } from 'react'

import { cn } from '@/lib/utils'

import {
  subscribeIntelligenceStream,
  type IntelligenceStreamItem,
} from './fusion-intelligence-bus'
import {
  requestGraphNodeFocus,
  setActiveDockTab,
  type FusionDockTab,
} from './fusion-sync-bus'
import { useEffect, useState } from 'react'

type Props = {
  className?: string
  variant?: 'ribbon' | 'panel'
  maxVisible?: number
  onReplayIndex?: (index: number) => void
}

const SEVERITY_BORDER: Record<string, string> = {
  critical: 'border-l-[var(--fusion-ops-red)]',
  warning: 'border-l-[var(--fusion-ops-yellow)]',
  info: 'border-l-[var(--fusion-ops-blue)]',
  clear: 'border-l-[var(--fusion-ops-cyan)]',
}

function formatTs(ts: number): string {
  return new Date(ts).toLocaleTimeString('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function handleItemAction(
  item: IntelligenceStreamItem,
  onReplayIndex?: (index: number) => void
): void {
  const action = item.action
  if (!action) {
    if (item.nodeId) requestGraphNodeFocus(item.nodeId)
    return
  }
  switch (action.type) {
    case 'focus_node':
    case 'fly_to':
      requestGraphNodeFocus(action.nodeId)
      break
    case 'open_dock':
      setActiveDockTab(action.tab as FusionDockTab)
      break
    case 'replay_index':
      onReplayIndex?.(action.index)
      break
    default:
      if (item.nodeId) requestGraphNodeFocus(item.nodeId)
  }
}

export function FusionIntelligenceStream({
  className,
  variant = 'panel',
  maxVisible = 24,
  onReplayIndex,
}: Props) {
  const [items, setItems] = useState<IntelligenceStreamItem[]>([])

  useEffect(() => subscribeIntelligenceStream(setItems), [])

  const visible = items.slice(0, maxVisible)

  const onClick = useCallback(
    (item: IntelligenceStreamItem) => {
      handleItemAction(item, onReplayIndex)
    },
    [onReplayIndex]
  )

  if (!visible.length) {
    return (
      <div
        className={cn(
          'flex h-full items-center justify-center fusion-text-micro text-[var(--fusion-text-tertiary)]',
          className
        )}
      >
        AWAITING INTELLIGENCE STREAM
      </div>
    )
  }

  if (variant === 'ribbon') {
    const line = visible
      .slice(0, 8)
      .map((i) => i.detail ?? i.title)
      .join('  ·  ')
    return (
      <div
        className={cn(
          'overflow-hidden whitespace-nowrap px-3 py-1.5 fusion-text-data min-w-0 flex-1',
          className
        )}
        role="log"
        aria-live="polite"
      >
        <span className="fusion-animate-feed-enter">{line}</span>
      </div>
    )
  }

  return (
    <ul
      className={cn('flex flex-col overflow-auto', className)}
      role="log"
      aria-live="polite"
      data-testid="fusion-intelligence-stream"
    >
      {visible.map((item) => (
        <li
          key={item.id}
          className={cn(
            'fusion-animate-feed-enter border-b border-[var(--fusion-border)] border-l-2 px-3 py-2 cursor-pointer hover:bg-[var(--fusion-bg-deck)]',
            SEVERITY_BORDER[item.severity ?? 'info']
          )}
          onClick={() => onClick(item)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              onClick(item)
            }
          }}
          role="button"
          tabIndex={0}
        >
          <div className="flex items-baseline gap-2">
            <span className="fusion-text-micro fusion-mono">{formatTs(item.ts)}</span>
            <span className="fusion-text-micro uppercase">{item.kind}</span>
            <span className="fusion-text-micro fusion-truncate">{item.title}</span>
          </div>
          {item.detail ? (
            <p className="mt-0.5 fusion-text-data fusion-truncate">{item.detail}</p>
          ) : null}
        </li>
      ))}
    </ul>
  )
}
