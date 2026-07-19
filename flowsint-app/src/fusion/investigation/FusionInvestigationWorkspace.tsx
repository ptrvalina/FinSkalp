import { useMemo, useCallback } from 'react'

import { useMutation } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { toast } from 'sonner'

import { FusionShell } from '../FusionShell'
import { FusionStitchHeader } from '../FusionStitchHeader'
import { FusionCanvasOS } from '../FusionCanvasOS'
import { FusionContextLens } from '../FusionContextLens'
import { FusionGraphStage } from '../FusionGraphStage'
import { FusionDock } from '../FusionDock'
import { FusionMioMissionStrip } from '../FusionMioMissionStrip'
import { FusionGraphScrubber } from '../FusionGraphScrubber'
import { FusionBriefLens } from '../FusionBriefLens'
import { FusionSeedLensOverlay } from '../FusionSeedLensOverlay'
import { FusionInspector } from '../FusionInspector'
import { FusionEvidenceDragPreview } from '../FusionEvidenceDragPreview'
import { FusionExecutiveBriefing } from '../FusionExecutiveBriefing'
import { FusionCaseSeedBar } from '../FusionCaseSeedBar'
import { FusionInvestigationStageRail } from '../FusionInvestigationStageRail'
import { resolveInvestigationPhase } from '../fusion-investigation-phase'

import {
  applySeedToCase,
  type StartInvestigationParams,
} from '@/fusion/fusion-investigation-start'
import { fusionCopy } from '@/fusion/fusion-copy'

import { useInvestigationWorkspace } from './useInvestigationWorkspace'
import {
  InvestigationContextPanels,
  InvestigationEvidencePanel,
  InvestigationEntityPanel,
} from './InvestigationContextPanels'
import { buildInvestigationDockTabs } from './buildInvestigationDockTabs'

import type { FusionOpsLens } from '@/fusion/FusionRail'

type Props = {
  caseRef: string
  lensSearch?: FusionOpsLens
}

export function FusionInvestigationWorkspace({ caseRef, lensSearch }: Props) {
  const navigate = useNavigate()
  const ws = useInvestigationWorkspace(caseRef, lensSearch)

  const applySeed = useMutation({
    mutationFn: (params: StartInvestigationParams) => applySeedToCase(caseRef, params),
    onSuccess: () => {
      ws.refreshSession()
      ws.setActiveLens('canvas')
      toast.info(fusionCopy.investigation.seedSavedRun)
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const nodeCount = ws.graphQuery.data?.nodes?.length ?? 0
  const showSeedBar = !ws.hasRealSeed || Boolean(ws.pipelineError) || nodeCount === 0
  const lastKyt = ws.lastKyt
  const hasWallet = Boolean(lastKyt?.address) || nodeCount > 0

  const phaseSnap = useMemo(
    () =>
      resolveInvestigationPhase({
        hasSeed: ws.hasRealSeed,
        nodeCount,
        pipelineActive: ws.pipelineActive,
        pipelineError: Boolean(ws.pipelineError),
        kytDone: Boolean(lastKyt?.address),
        kytApplicable: hasWallet,
        fusionDone: ws.fusionDone,
      }),
    [
      ws.hasRealSeed,
      nodeCount,
      ws.pipelineActive,
      ws.pipelineError,
      lastKyt?.address,
      hasWallet,
      ws.fusionDone,
    ]
  )

  const stageBusy =
    ws.pipelineActive ||
    ws.fuseMutation.isPending ||
    ws.screenMutation.isPending ||
    ws.batchRunning

  const handleStageNext = useCallback(() => {
    switch (phaseSnap.nextActionKind) {
      case 'collect':
        if (!ws.hasRealSeed) {
          ws.setActiveLens('collect')
          return
        }
        ws.retryPipeline()
        return
      case 'kyt': {
        const card = ws.mioCards.find((c) => c.actionKind === 'screen_wallet')
        if (card) {
          void ws.executeMioCard(card)
          return
        }
        toast.info('KYT-карточка не найдена — откройте MIO внизу')
        return
      }
      case 'fuse':
        if (!ws.caseId) {
          toast.error('Дело не найдено')
          return
        }
        ws.fuseMutation.mutate()
        return
      case 'reports':
        void navigate({
          to: '/dashboard/fusion/reports/$caseRef',
          params: { caseRef },
        })
        return
      default:
        return
    }
  }, [phaseSnap.nextActionKind, ws, navigate, caseRef])

  const dockTabs = useMemo(
    () =>
      buildInvestigationDockTabs({
        timelineEvents: ws.timelineEvents,
        evidenceItems: ws.evidenceItems,
        selectedEvidenceId: ws.selectedEvidenceId,
        handleEvidenceClick: ws.handleEvidenceClick,
        resolveEvidenceNodeId: ws.resolveEvidenceNodeId,
        workspaceQuery: ws.workspaceQuery,
        graphQuery: ws.graphQuery,
        screenMutation: ws.screenMutation,
        caseRef: ws.caseRef,
        caseId: ws.caseId,
        fusion: ws.fusion,
      }),
    [
      ws.timelineEvents,
      ws.evidenceItems,
      ws.selectedEvidenceId,
      ws.handleEvidenceClick,
      ws.resolveEvidenceNodeId,
      ws.workspaceQuery,
      ws.graphQuery,
      ws.screenMutation,
      ws.caseRef,
      ws.caseId,
      ws.fusion,
    ]
  )

  return (
    <FusionShell
      graphOs
      activeLens={ws.activeLens}
      onLensChange={ws.setActiveLens}
      queueBadgeCount={ws.queueData.length}
      stitchHeader={
        <FusionStitchHeader
          caseRef={caseRef}
          sessionLabel={`${nodeCount} nodes`}
          phaseLabel={phaseSnap.nowLabel}
          phaseTone={
            phaseSnap.finished ? 'done' : phaseSnap.currentId === 'collect' && ws.pipelineError ? 'error' : 'active'
          }
          live={!ws.livePaused}
          onRunCollection={ws.retryPipeline}
          runDisabled={Boolean(ws.pipelineActive && !ws.pipelineError)}
          runLabel={
            ws.hasRealSeed
              ? fusionCopy.investigation.runCollectors
              : fusionCopy.graph.collectSeed
          }
        />
      }
      contextBar={
        <>
          <FusionInvestigationStageRail
            phase={phaseSnap}
            busy={stageBusy}
            onNext={handleStageNext}
          />
          {showSeedBar ? (
            <FusionCaseSeedBar
              caseRef={caseRef}
              onUpdated={ws.refreshSession}
              onRunPipeline={ws.retryPipeline}
            />
          ) : null}
        </>
      }
      executiveBriefing={
        <FusionExecutiveBriefing
          liveEvents={ws.liveEvents}
          mioCards={ws.mioCards}
          graphNodeCount={ws.graphQuery.data?.nodes?.length}
          highestRiskNodeLabel={ws.evolution.highestRiskNodeLabel}
          moneyFlowSummary={ws.evolution.moneyFlowSummary}
        />
      }
      activeSection="graph"
      caseRef={caseRef}
      workflowStatus={ws.caseQuery.data?.workflow_status ?? ws.matchedCase?.workflow_status}
      fusionDone={ws.fusionDone}
      onGenerateReport={() => {
        void navigate({
          to: '/dashboard/fusion/reports/$caseRef',
          params: { caseRef },
        })
      }}
      onCreateEvidence={() => ws.setDockTab('evidence')}
    >
      <FusionCanvasOS
        leftPanelTitle="Discovery Panel"
        leftPanelSubtitle="Connection logic · depth · evidence"
        leftPanel={
          <FusionContextLens
            className="stitch-discovery-panel h-full"
            collapsed={ws.contextCollapsed}
            onCollapsedChange={ws.setContextCollapsed}
            chrono={
              <InvestigationContextPanels ws={ws} timelineItemRefs={ws.timelineItemRefs} />
            }
            evidence={
              <InvestigationEvidencePanel
                evidenceItems={ws.evidenceItems}
                selectedEvidenceId={ws.selectedEvidenceId}
                onEvidenceClick={ws.handleEvidenceClick}
              />
            }
            entity={
              <InvestigationEntityPanel
                selectedNodeId={ws.selectedNodeId}
                lastKyt={ws.lastKyt}
                latestRisk={ws.latestRisk}
                nodeLabel={
                  ws.graphQuery.data?.nodes?.find((n) => n.id === ws.selectedNodeId)?.label ?? null
                }
              />
            }
          />
        }
        rightPanel={
          ws.selectedNodeId ? (
            <FusionInspector
              graph={ws.graphQuery.data}
              nodeId={ws.selectedNodeId}
              onClose={() => ws.setSelectedNodeId(null)}
              onExpand={(id) => {
                ws.setSelectedNodeId(id)
                ws.setHopLensMaxDepth(2)
              }}
            />
          ) : (
            <InvestigationEntityPanel
              selectedNodeId={ws.selectedNodeId}
              lastKyt={ws.lastKyt}
              latestRisk={ws.latestRisk}
              nodeLabel={
                ws.graphQuery.data?.nodes?.find((n) => n.id === ws.selectedNodeId)?.label ?? null
              }
            />
          )
        }
        rightPanelFooter={
          <button
            type="button"
            className="stitch-dossier-panel__export"
            onClick={() => {
              void navigate({
                to: '/dashboard/fusion/reports/$caseRef',
                params: { caseRef },
              })
            }}
          >
            Export Full Report
          </button>
        }
        graph={
          <>
            <FusionGraphStage
              graph={ws.graphQuery.data}
              loading={ws.graphQuery.isLoading}
              alerts={ws.graphAlerts}
              caseRef={caseRef}
              live={!ws.livePaused && ws.liveEvents.length > 0}
              persistent
              crossCaseLinks={ws.crossLinksQuery.data?.links ?? []}
              detachHref={ws.graphDetachUrl}
              selectedNodeId={ws.selectedNodeId}
              onNodeSelect={ws.handleGraphNodeSelect}
              highlightNodeIds={ws.highlightNodeIds}
              replayIndex={ws.replayIndex}
              onReplayIndexChange={ws.setReplayIndex}
              hopLensMaxDepth={ws.hopLensMaxDepth}
              onHopLensMaxDepthChange={ws.setHopLensMaxDepth}
              hopLensOriginId={ws.selectedNodeId}
              onEvidenceDrop={ws.handleEvidenceDrop}
              investigationMode
              initialReactFlowCamera={ws.evolution.initialReactFlowCamera}
              onReactFlowCameraChange={ws.evolution.onReactFlowCameraChange}
              initialGpuCamera={ws.evolution.initialGpuCamera}
              onGpuCameraChange={ws.evolution.onGpuCameraChange}
              onGraphDiff={ws.evolution.onGraphDiff}
              onRequestCollect={() => ws.setActiveLens('collect')}
              systemsHud={{
                scalpelLive: ws.pipelineActive && ws.pipelinePhase === 'collectors',
                nodeCount: ws.graphQuery.data?.nodes?.length ?? 0,
                riskLogicOk: !ws.pipelineError,
              }}
              className="h-full min-h-full border-0 rounded-none fusion-graph-stage--dominant stitch-graph-stage"
            />
            <FusionSeedLensOverlay
              open={ws.activeLens === 'collect'}
              onClose={() => ws.setActiveLens('canvas')}
              onSubmit={(params) => applySeed.mutate(params)}
              isSubmitting={applySeed.isPending}
            />
            <FusionBriefLens
              open={ws.activeLens === 'brief'}
              onClose={() => ws.setActiveLens('canvas')}
              liveEvents={ws.liveEvents}
              mioCards={ws.mioCards}
              graphNodeCount={ws.graphQuery.data?.nodes?.length}
              highestRiskNodeLabel={ws.evolution.highestRiskNodeLabel}
              moneyFlowSummary={ws.evolution.moneyFlowSummary}
            />
          </>
        }
        operations={
          <FusionMioMissionStrip
            cards={ws.mioCards}
            livePulse={ws.livePulse}
            canExecute={ws.canExecute}
            batchRunning={ws.batchRunning}
            batchProgress={ws.batchProgress}
            onExecute={ws.executeMioCard}
            onDefer={(id) => ws.setDismissedCards((p) => [...p, id])}
            onExecAll={() => void ws.handleExecAll()}
            onCancelBatch={ws.cancelBatch}
          />
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
            defaultTab="evidence"
            activeTab={ws.dockTab}
            onTabChange={ws.setDockTab}
          />
        }
      />

      <FusionEvidenceDragPreview containerRef={ws.graphContainerRef} />
    </FusionShell>
  )
}
