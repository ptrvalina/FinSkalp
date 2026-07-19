import { useMemo } from 'react'

import { FusionShell } from '../FusionShell'
import { FusionGraphStage } from '../FusionGraphStage'
import { FusionExecutiveBriefing } from '../FusionExecutiveBriefing'
import { FusionDock } from '../FusionDock'
import { FusionInspector } from '../FusionInspector'
import { FusionCanvasOS } from '../FusionCanvasOS'
import { FusionStitchHeader } from '../FusionStitchHeader'
import { FusionMioMissionStrip } from '../FusionMioMissionStrip'
import { FusionSeedLensOverlay } from '../FusionSeedLensOverlay'
import { FusionEmptyState } from '../FusionEmptyState'
import { FusionQueuePanel } from '../FusionQueuePanel'
import { FusionGraphScrubber } from '../FusionGraphScrubber'
import { FusionInvestigationStageRail } from '../FusionInvestigationStageRail'

import { useInvestigationLaunch } from '@/fusion/useInvestigationLaunch'

import { fusionCopy } from '@/fusion/fusion-copy'

import { useMissionControlWorkspace } from './useMissionControlWorkspace'
import { buildMissionControlDockTabs } from './buildMissionControlDockTabs'

import type { FusionOpsLens } from '@/fusion/FusionRail'

const EMPTY_HIGHLIGHTS: string[] = []

type Props = {
  lensSearch?: FusionOpsLens
}

export function FusionMissionControlWorkspace({ lensSearch }: Props) {
  const launch = useInvestigationLaunch()
  const ws = useMissionControlWorkspace(lensSearch)

  const dockTabs = useMemo(
    () =>
      buildMissionControlDockTabs({
        timelineEvents: ws.timelineEvents,
        evidenceItems: ws.evidenceItems,
        selectedEvidenceId: ws.selectedEvidenceId,
        handleEvidenceClick: ws.handleEvidenceClick,
        workspaceQuery: ws.workspaceQuery,
        graphQuery: ws.graphQuery,
        previewCaseRef: ws.previewCaseRef,
        previewCaseId: ws.previewCaseId,
        fusion: ws.fusion,
        queueData: ws.queueData,
      }),
    [
      ws.timelineEvents,
      ws.evidenceItems,
      ws.selectedEvidenceId,
      ws.handleEvidenceClick,
      ws.workspaceQuery,
      ws.graphQuery,
      ws.previewCaseRef,
      ws.previewCaseId,
      ws.fusion,
      ws.queueData,
    ]
  )

  return (
    <FusionShell
      graphOs
      activeLens={ws.activeLens}
      onLensChange={ws.setActiveLens}
      queueBadgeCount={ws.queueData.length}
      activeSection="command"
      caseRef={ws.previewCaseRef}
      workflowStatus={ws.previewCaseQuery.data?.workflow_status}
      fusionDone={ws.fusionDone}
      stitchHeader={
        <FusionStitchHeader
          caseRef={ws.previewCaseRef}
          sessionLabel={`${ws.queueData.length} cases · ${ws.graphQuery.data?.nodes?.length ?? 0} nodes`}
          phaseLabel={ws.phaseSnap.nowLabel}
          phaseTone={ws.phaseSnap.finished ? 'done' : 'active'}
          live={!ws.livePaused}
          onRunCollection={() => ws.setActiveLens('collect')}
          runLabel={fusionCopy.missionControl.collectSeed}
        />
      }
      contextBar={
        ws.previewCaseRef ? (
          <FusionInvestigationStageRail
            phase={ws.phaseSnap}
            busy={ws.batchRunning || ws.fuseMutation.isPending || ws.screenMutation.isPending}
            onNext={() => void ws.handleStageNext()}
          />
        ) : null
      }
      executiveBriefing={
        <FusionExecutiveBriefing
          liveEvents={ws.liveEvents}
          mioCards={ws.mioCards}
          queueRows={ws.queueData as Parameters<typeof FusionExecutiveBriefing>[0]['queueRows']}
          graphNodeCount={ws.graphQuery.data?.nodes?.length}
        />
      }
    >
      <FusionCanvasOS
        leftPanelTitle="Case Queue"
        leftPanelSubtitle={`${ws.queueData.length} active · SLA priority`}
        leftPanel={
          <FusionQueuePanel
            className="stitch-queue-panel"
            rows={ws.queueData}
            activeCaseRef={ws.previewCaseRef}
            onSelectPreview={(row) => ws.setPreviewCase(row.case_ref ?? row.case_id)}
            onStartCollect={() => ws.setActiveLens('collect')}
          />
        }
        graph={
          <>
            {!ws.previewCaseId && !ws.graphQuery.isLoading ? (
              <FusionEmptyState
                className="absolute inset-0 z-[3] bg-[var(--fusion-bg-void)]"
                title={fusionCopy.missionControl.emptyQueueTitle}
                description={fusionCopy.missionControl.emptyQueueDescription}
                action={
                  <div className="flex flex-wrap justify-center gap-2">
                    <button
                      type="button"
                      className="fusion-text-micro rounded border border-[var(--fusion-border)] px-3 py-1.5 text-[var(--fusion-ops-blue)]"
                      onClick={() => ws.setActiveLens('collect')}
                    >
                      {fusionCopy.missionControl.collectSeed}
                    </button>
                    <button
                      type="button"
                      className="fusion-text-micro rounded border border-[var(--fusion-border)] px-3 py-1.5"
                      onClick={() => ws.setActiveLens('queue')}
                    >
                      {fusionCopy.missionControl.queue}
                    </button>
                  </div>
                }
              />
            ) : null}
            <FusionGraphStage
              graph={ws.graphQuery.data}
              loading={ws.graphQuery.isLoading}
              alerts={ws.graphAlerts}
              caseRef={ws.previewCaseRef}
              persistent
              investigationMode
              live={!ws.livePaused && ws.liveEvents.length > 0}
              livePaused={ws.livePaused}
              selectedNodeId={ws.selectedNodeId}
              onNodeSelect={ws.setSelectedNodeId}
              highlightNodeIds={ws.selectedNodeId ? [ws.selectedNodeId] : EMPTY_HIGHLIGHTS}
              replayIndex={ws.replayIndex}
              onReplayIndexChange={ws.setReplayIndex}
              onEvidenceDrop={ws.handleEvidenceDrop}
              onGraphDiff={ws.onGraphDiff}
              onRequestCollect={() => ws.setActiveLens('collect')}
              className="h-full min-h-full border-0 rounded-none fusion-graph-stage--dominant stitch-graph-stage"
            />
            <FusionSeedLensOverlay
              open={ws.activeLens === 'collect'}
              onClose={() => ws.setActiveLens('canvas')}
              onSubmit={(params) => launch.mutate(params)}
              isSubmitting={launch.isPending}
            />
          </>
        }
        operations={
          <FusionMioMissionStrip
            cards={ws.mioCards}
            livePulse={ws.livePulse}
            canExecute={ws.canExecute}
            batchRunning={ws.batchRunning}
            onExecute={ws.handleExecuteCard}
            onDefer={(id) => ws.setDismissedCards((p) => [...p, id])}
            onExecAll={() => void ws.handleExecAll()}
          />
        }
        rightPanel={
          ws.selectedNodeId ? (
            <FusionInspector
              graph={ws.graphQuery.data}
              nodeId={ws.selectedNodeId}
              onClose={() => ws.setSelectedNodeId(null)}
            />
          ) : undefined
        }
        timeline={
          <>
            <span>T-MINUS 30D</span>
            <div className="min-w-0 flex-1">
              <FusionGraphScrubber
                replaySteps={ws.replaySteps}
                replayIndex={ws.replayIndex}
                onReplayIndexChange={ws.setReplayIndex}
                timelineEvents={ws.timelineEvents}
              />
            </div>
            <span className="text-[var(--fusion-ops-blue)]">PRESENT</span>
          </>
        }
        dock={
          <FusionDock
            tabs={dockTabs}
            defaultTab="timeline"
            activeTab={ws.dockTab}
            onTabChange={ws.setDockTab}
          />
        }
      />
    </FusionShell>
  )
}
