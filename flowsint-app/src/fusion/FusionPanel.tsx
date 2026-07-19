import { useCallback, useState, type ReactNode } from 'react'
import { ExternalLink, PanelBottomClose, Pin } from 'lucide-react'
import { cn } from '@/lib/utils'
import { loadFusionPanelPins, toggleFusionPanelPin } from './fusion-layout-storage'

type Props = {
  id: string
  title: string
  children: ReactNode
  className?: string
  defaultPinned?: boolean
  onCollapse?: () => void
  detachHref?: string
  detachTitle?: string
}

export function FusionPanel({
  id,
  title,
  children,
  className,
  defaultPinned = false,
  onCollapse,
  detachHref,
  detachTitle = 'Open in new window',
}: Props) {
  const [pinned, setPinned] = useState(() => {
    const pins = loadFusionPanelPins()
    return pins.includes(id) || defaultPinned
  })

  const handlePin = useCallback(() => {
    const next = toggleFusionPanelPin(id)
    setPinned(next.includes(id))
  }, [id])

  return (
    <div className={cn('fusion-panel fusion-animate-panel-in', pinned && 'fusion-panel--pinned', className)}>
      <header className="fusion-panel__header">
        <span className="fusion-panel__title">{title}</span>
        <div className="fusion-panel__actions">
          <button
            type="button"
            className={cn('fusion-panel__btn', pinned && 'fusion-panel__btn--active')}
            onClick={handlePin}
            aria-label={pinned ? 'Unpin panel' : 'Pin panel'}
            title={pinned ? 'Unpin' : 'Pin'}
          >
            <Pin className="h-3 w-3" />
          </button>
          {onCollapse ? (
            <button
              type="button"
              className="fusion-panel__btn"
              onClick={onCollapse}
              aria-label="Collapse panel"
              title="Collapse"
            >
              <PanelBottomClose className="h-3 w-3" />
            </button>
          ) : null}
          {detachHref ? (
            <a
              href={detachHref}
              target="_blank"
              rel="noreferrer"
              className="fusion-panel__btn"
              aria-label={detachTitle}
              title={detachTitle}
            >
              <ExternalLink className="h-3 w-3" />
            </a>
          ) : (
            <button
              type="button"
              className="fusion-panel__btn"
              aria-label="Detach panel"
              title="Multi-monitor detach — set detachHref"
              disabled
            >
              <ExternalLink className="h-3 w-3" />
            </button>
          )}
        </div>
      </header>
      <div className="fusion-panel__body">{children}</div>
    </div>
  )
}
