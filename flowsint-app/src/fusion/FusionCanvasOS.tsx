import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

type Props = {
  graph: ReactNode
  /** Discovery panel (investigation) or case queue (mission control). */
  leftPanel?: ReactNode
  leftPanelTitle?: string
  leftPanelSubtitle?: string
  /** Entity forensic dossier (investigation). */
  rightPanel?: ReactNode
  rightPanelTitle?: string
  rightPanelSubtitle?: string
  rightPanelFooter?: ReactNode
  operations?: ReactNode
  overlays?: ReactNode
  dock?: ReactNode
  timeline?: ReactNode
  className?: string
}

/** Canvas: discovery | graph | dossier | dock + timeline. */
export function FusionCanvasOS({
  graph,
  leftPanel,
  leftPanelTitle = 'Discovery Panel',
  leftPanelSubtitle = 'Filtering connection types',
  rightPanel,
  rightPanelTitle = 'Entity Context',
  rightPanelSubtitle = 'Active Intelligence',
  rightPanelFooter,
  operations,
  overlays,
  dock,
  timeline,
  className,
}: Props) {
  return (
    <div className={cn('fusion-canvas-os flex min-h-0 flex-1 flex-col', className)} data-testid="fusion-canvas-os">
      <div className="fusion-canvas-os__workspace flex min-h-0 flex-1 overflow-hidden">
        {leftPanel ? (
          <aside className="stitch-side-panel" data-testid="fusion-discovery-panel">
            <div className="stitch-side-panel__head">
              <p className="stitch-side-panel__title">{leftPanelTitle}</p>
              {leftPanelSubtitle ? <p className="stitch-side-panel__sub">{leftPanelSubtitle}</p> : null}
            </div>
            <div className="stitch-side-panel__body">{leftPanel}</div>
          </aside>
        ) : null}
        <div className="fusion-canvas-os__graph-column min-w-0 flex-1">
          <div className="fusion-canvas-os__graph-slot stitch-canvas-bg">
            {graph}
            {overlays}
          </div>
          {operations ? <div className="fusion-canvas-os__ops">{operations}</div> : null}
        </div>
        {rightPanel ? (
          <aside className="stitch-dossier-panel" data-testid="fusion-entity-dossier">
            <div className="stitch-dossier-panel__head">
              <div>
                <p className="stitch-dossier-panel__title">{rightPanelTitle}</p>
                <p className="stitch-dossier-panel__subtitle">{rightPanelSubtitle}</p>
              </div>
            </div>
            <div className="stitch-dossier-panel__body">{rightPanel}</div>
            {rightPanelFooter ? (
              <div className="stitch-dossier-panel__footer">{rightPanelFooter}</div>
            ) : null}
          </aside>
        ) : null}
      </div>
      {dock ? <section className="fusion-canvas-os__dock">{dock}</section> : null}
      {timeline ? <footer className="stitch-timeline-footer">{timeline}</footer> : null}
    </div>
  )
}
