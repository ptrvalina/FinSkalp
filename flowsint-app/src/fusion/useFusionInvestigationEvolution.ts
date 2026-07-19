/**
 * Investigation workspace session sync + intelligence stream wiring (U1–U4).
 * Import into investigation route to avoid duplicating persistence logic.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import type { EvidenceGraph } from '@/api/compliance-service'
import type { ComplianceLiveEvent } from '@/hooks/use-compliance-events'

import { clearIntelligenceStream } from './fusion-intelligence-bus'
import type { GraphDiffEvent } from './fusion-graph-diff'
import { loadCaseSession, mergeCaseSession, defaultGraphLayersFromSession, gpuCameraFromSession } from './fusion-case-session'
import type { MioExecutableCard } from './fusion-mio-actions'
import { setGraphLayers, setLivePaused, setMoneyFlowEnabled } from './fusion-sync-bus'
import { useFusionIntelligenceStream } from './useFusionIntelligenceStream'

type EvidenceItem = {
  id: string
  source_type: string
  content_hash: string
  status?: string
  payload?: Record<string, unknown>
}

export type InvestigationSessionSnapshot = {
  selectedNodeId: string | null
  selectedTimelineEventId: string | null
  selectedEvidenceId: string | null
  replayIndex: number
  hopLensMaxDepth: number | null
  dockTab: string
  leftTab: 'timeline' | 'hypotheses'
  livePaused: boolean
}

export function readInvestigationSession(caseRef: string): InvestigationSessionSnapshot {
  const s = loadCaseSession(caseRef)
  return {
    selectedNodeId: s.selectedNodeId ?? null,
    selectedTimelineEventId: s.selectedTimelineEventId ?? null,
    selectedEvidenceId: s.selectedEvidenceId ?? null,
    replayIndex: s.replayIndex ?? 0,
    hopLensMaxDepth: s.hopLensMaxDepth ?? null,
    dockTab: s.dockTab ?? 'evidence',
    leftTab: s.leftTab ?? 'timeline',
    livePaused: s.livePaused ?? false,
  }
}

type Params = {
  caseRef: string
  liveEvents: ComplianceLiveEvent[]
  mioCards: MioExecutableCard[]
  evidenceItems: EvidenceItem[]
  graph?: EvidenceGraph | null
  snapshot: InvestigationSessionSnapshot
}

export function useFusionInvestigationEvolution({
  caseRef,
  liveEvents,
  mioCards,
  evidenceItems,
  graph,
  snapshot,
}: Params) {
  const [graphDiffEvents, setGraphDiffEvents] = useState<GraphDiffEvent[]>([])
  const sessionBooted = useRef(false)

  useEffect(() => {
    clearIntelligenceStream()
    sessionBooted.current = false
    const s = loadCaseSession(caseRef)
    if (s.graphLayers) setGraphLayers(s.graphLayers)
    if (s.moneyFlowEnabled != null) setMoneyFlowEnabled(s.moneyFlowEnabled)
    if (s.livePaused != null) setLivePaused(s.livePaused)
    sessionBooted.current = true
  }, [caseRef])

  useFusionIntelligenceStream({
    caseRef,
    liveEvents,
    mioCards,
    graphDiffEvents,
    evidenceItems,
    enabled: Boolean(caseRef),
  })

  const persist = useCallback(
    (partial: Partial<InvestigationSessionSnapshot & ReturnType<typeof loadCaseSession>>) => {
      if (!sessionBooted.current) return
      mergeCaseSession(caseRef, partial)
    },
    [caseRef]
  )

  useEffect(() => {
    persist({
      selectedNodeId: snapshot.selectedNodeId,
      selectedTimelineEventId: snapshot.selectedTimelineEventId,
      selectedEvidenceId: snapshot.selectedEvidenceId,
      replayIndex: snapshot.replayIndex,
      hopLensMaxDepth: snapshot.hopLensMaxDepth,
      dockTab: snapshot.dockTab,
      leftTab: snapshot.leftTab,
      livePaused: snapshot.livePaused,
    })
  }, [persist, snapshot])

  const initialReactFlowCamera = useMemo(() => {
    const s = loadCaseSession(caseRef)
    return s.reactFlowCamera
  }, [caseRef])

  const onReactFlowCameraChange = useCallback(
    (camera: { x: number; y: number; zoom: number }) => {
      persist({ reactFlowCamera: camera })
    },
    [persist]
  )

  const initialGpuCamera = useMemo(() => gpuCameraFromSession(caseRef), [caseRef])

  const onGpuCameraChange = useCallback(
    (camera: { x: number; y: number; ratio: number }) => {
      persist({ gpuCamera: camera })
    },
    [persist]
  )

  const getFloatPosition = useCallback(
    (panelId: string) => loadCaseSession(caseRef).floatPositions?.[panelId],
    [caseRef]
  )

  const onFloatPositionChange = useCallback(
    (panelId: string, position: { x: number; y: number }) => {
      const prev = loadCaseSession(caseRef)
      persist({
        floatPositions: { ...prev.floatPositions, [panelId]: position },
      })
    },
    [caseRef, persist]
  )

  const onGraphDiff = useCallback((events: GraphDiffEvent[]) => {
    setGraphDiffEvents((prev) => [...events, ...prev].slice(0, 40))
  }, [])

  const highestRiskNodeLabel = useMemo(() => {
    if (!graph?.nodes?.length) return null
    let best: { label: string; score: number } | null = null
    for (const node of graph.nodes) {
      const raw = (node as { risk_score?: number }).risk_score
      if (typeof raw !== 'number') continue
      if (!best || raw > best.score) {
        best = { label: node.label ?? node.id, score: raw }
      }
    }
    return best?.label ?? graph.nodes[0]?.label ?? null
  }, [graph])

  const moneyFlowSummary = useMemo(() => {
    const edges = graph?.edges?.length ?? 0
    return edges ? `${edges} flows tracked · overlay ON` : 'Awaiting graph edges'
  }, [graph])

  return {
    graphDiffEvents,
    onGraphDiff,
    initialReactFlowCamera,
    onReactFlowCameraChange,
    initialGpuCamera,
    onGpuCameraChange,
    getFloatPosition,
    onFloatPositionChange,
    persistAction: (action: string) => mergeCaseSession(caseRef, { lastAction: action, lastActionAt: Date.now() }),
    highestRiskNodeLabel,
    moneyFlowSummary,
    initialGraphLayers: defaultGraphLayersFromSession(loadCaseSession(caseRef)),
  }
}
