import type { ReactNode } from 'react'

import { FusionCanvasOS } from './FusionCanvasOS'
import { FusionContextLens } from './FusionContextLens'

type Props = {
  chrono: ReactNode
  evidence: ReactNode
  entity: ReactNode
  graph: ReactNode
  scrubber?: ReactNode
  operations: ReactNode
  dock?: ReactNode
  overlays?: ReactNode
  rightPanel?: ReactNode
  contextCollapsed?: boolean
  onContextCollapsedChange?: (v: boolean) => void
}

/** Investigation workspace — Stitch Relationship Explorer layout. */
export function InvestigationGraphOSLayout({
  chrono,
  evidence,
  entity,
  graph,
  scrubber,
  operations,
  dock,
  overlays,
  rightPanel,
  contextCollapsed,
  onContextCollapsedChange,
}: Props) {
  return (
    <FusionCanvasOS
      leftPanelTitle="Discovery Panel"
      leftPanelSubtitle="Filtering connection types"
      leftPanel={
        <FusionContextLens
          className="stitch-discovery-panel h-full"
          chrono={chrono}
          evidence={evidence}
          entity={entity}
          collapsed={contextCollapsed}
          onCollapsedChange={onContextCollapsedChange}
        />
      }
      rightPanel={rightPanel}
      graph={
        <>
          <div className="relative h-full min-h-0 flex-1">{graph}</div>
          {overlays}
        </>
      }
      operations={operations}
      dock={dock}
      timeline={scrubber}
    />
  )
}
