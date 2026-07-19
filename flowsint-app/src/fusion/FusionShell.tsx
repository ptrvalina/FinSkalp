import type { ReactNode } from 'react'
import { useEffect, useState } from 'react'

import { cn } from '@/lib/utils'

import { FusionKeyboardProvider } from './FusionKeyboard'
import { FusionLiveAnnouncerProvider } from './useFusionAnnouncer'
import { FusionMissionStrip, type FusionMissionStripData } from './FusionMissionStrip'
import { FusionRail, type FusionOpsLens } from './FusionRail'
import { FusionStrPipeline } from './FusionStrPipeline'
import { subscribeFusionSync } from './fusion-sync-bus'

type Props = {
  children: ReactNode
  mission?: FusionMissionStripData
  intelligenceRibbon?: ReactNode
  contextBar?: ReactNode
  executiveBriefing?: ReactNode
  telemetry?: ReactNode
  stitchHeader?: ReactNode
  activeSection?: 'command' | 'investigate' | 'intelligence' | 'graph' | 'queue' | 'legacy'
  activeLens?: FusionOpsLens
  onLensChange?: (lens: FusionOpsLens) => void
  graphOs?: boolean
  queueBadgeCount?: number
  caseRef?: string | null
  workflowStatus?: string | null
  fusionDone?: boolean
  showStrPipeline?: boolean
  onGenerateReport?: () => void
  onCreateEvidence?: () => void
}

export function FusionShell({
  children,
  mission,
  intelligenceRibbon,
  contextBar,
  executiveBriefing,
  telemetry,
  stitchHeader,
  activeSection = 'command',
  activeLens = 'canvas',
  onLensChange,
  graphOs = false,
  queueBadgeCount,
  caseRef,
  workflowStatus,
  fusionDone = false,
  showStrPipeline = false,
  onGenerateReport,
  onCreateEvidence,
}: Props) {
  const [executiveMode, setExecutiveMode] = useState(false)

  useEffect(() => {
    return subscribeFusionSync((sync) => setExecutiveMode(sync.executiveMode))
  }, [])

  return (
    <FusionLiveAnnouncerProvider>
      <FusionKeyboardProvider
        caseRef={caseRef}
        onGenerateReport={onGenerateReport}
        onCreateEvidence={onCreateEvidence}
      >
        <div
          className={cn(
            'fusion-root fusion-shell',
            graphOs && 'fusion-shell--graph-os',
            executiveMode && 'fusion-shell--executive'
          )}
          data-fusion
          data-fusion-graph-os={graphOs ? 'true' : undefined}
          data-fusion-executive={executiveMode ? 'true' : undefined}
        >
          <FusionRail
            activeSection={activeSection}
            caseRef={caseRef}
            graphOs={graphOs}
            activeLens={activeLens}
            onLensChange={onLensChange}
            queueBadgeCount={queueBadgeCount}
          />
          <div className="fusion-shell__main">
            {graphOs ? (
              stitchHeader ?? (telemetry ? <div className="fusion-telemetry-ribbon">{telemetry}</div> : null)
            ) : (
              <>
                {showStrPipeline ? (
                  <FusionStrPipeline workflowStatus={workflowStatus} fusionDone={fusionDone} />
                ) : null}
                {mission ? <FusionMissionStrip data={mission} /> : null}
              </>
            )}
            {contextBar ? <div className="fusion-inv-context">{contextBar}</div> : null}
            {!graphOs && intelligenceRibbon ? (
              <div className="fusion-intelligence-ribbon">{intelligenceRibbon}</div>
            ) : null}
            <div className="fusion-shell__body">{children}</div>
          </div>
          {executiveBriefing}
        </div>
      </FusionKeyboardProvider>
    </FusionLiveAnnouncerProvider>
  )
}
