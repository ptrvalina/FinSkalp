import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { Link } from '@tanstack/react-router'

import type { CrossCaseGraphLink, EvidenceGraph } from '@/api/compliance-service'

import { ComplianceGraphView } from '@/components/compliance/compliance-graph-view'

import { cn } from '@/lib/utils'

import { computeHopDistances, exportGraphSnapshot } from './fusion-graph-utils'
import { diffEvidenceGraphs, diffNodeIds, type GraphDiffEvent } from './fusion-graph-diff'
import {
  subscribeFusionSync,
  getFusionSyncState,
  setExecutiveMode,
} from './fusion-sync-bus'
import { FusionCinematicTour } from './FusionCinematicTour'
import { FusionGpuGraphView } from './FusionGpuGraphView'
import { FusionGraphLayerToggles } from './FusionGraphLayerToggles'
import { FusionGraphSearchPanel } from './FusionGraphSearchPanel'
import type { GraphLayerToggles } from './fusion-graph-layers'
import { DEFAULT_GRAPH_LAYERS } from './fusion-graph-layers'
import { LARGE_GRAPH_THRESHOLD, INVESTIGATION_GPU_THRESHOLD } from './fusion-gpu-graph-engine'
import { isGpuGraphEnabled } from './fusion-layout-presets'
import { useFusionCollaboration, FusionCollaborationOverlay } from './fusion-collaboration'
import { FusionCollaborationPresence } from './FusionCollaborationPresence'
import { FusionSkeleton } from './FusionSkeleton'
import { FusionEmptyState } from './FusionEmptyState'
import { fusionCopy } from './fusion-copy'
import { FusionSystemsHud } from './FusionSystemsHud'
import { useFusionAnnouncer } from './useFusionAnnouncer'

import { toast } from 'sonner'

type GraphAlert = {
  nodeId?: string
  type?: string
}

type Props = {
  graph?: EvidenceGraph | null
  loading?: boolean
  alerts?: GraphAlert[]
  caseRef?: string | null
  compact?: boolean
  live?: boolean
  livePaused?: boolean
  persistent?: boolean
  centerGraphTrigger?: number
  className?: string
  crossCaseLinks?: CrossCaseGraphLink[]
  detachHref?: string
  selectedNodeId?: string | null
  onNodeSelect?: (nodeId: string | null) => void
  highlightNodeIds?: string[]
  replayIndex?: number
  onReplayIndexChange?: (index: number) => void
  hopLensEnabled?: boolean
  hopLensMaxDepth?: number | null
  onHopLensMaxDepthChange?: (depth: number | null) => void
  hopLensOriginId?: string | null
  focusNodeId?: string | null
  cinematic?: boolean
  onCinematicChange?: (active: boolean) => void
  onEvidenceDrop?: (evidenceHash: string, nodeId: string | null) => void
  collaborationEnabled?: boolean
  /** Investigation workspace — prefer WebGL from INVESTIGATION_GPU_THRESHOLD (500). */
  investigationMode?: boolean
  initialReactFlowCamera?: { x: number; y: number; zoom: number }
  onReactFlowCameraChange?: (camera: { x: number; y: number; zoom: number }) => void
  initialGpuCamera?: { x: number; y: number; ratio: number }
  onGpuCameraChange?: (camera: { x: number; y: number; ratio: number }) => void
  onGraphDiff?: (events: GraphDiffEvent[]) => void
  onRequestCollect?: () => void
  /** Bottom-left systems HUD (investigation Graph OS). */
  systemsHud?: {
    scalpelLive?: boolean
    nodeCount?: number
    riskLogicOk?: boolean
  }
}

function computeHopDepth(graph?: EvidenceGraph | null): number {
  if (!graph?.nodes?.length) return 0

  const incoming = new Map<string, number>()
  graph.nodes.forEach((n) => incoming.set(n.id, 0))
  graph.edges.forEach((e) => {
    incoming.set(e.target, (incoming.get(e.target) ?? 0) + 1)
  })
  const roots = graph.nodes.filter((n) => (incoming.get(n.id) ?? 0) === 0).map((n) => n.id)
  const start = roots.length ? roots : [graph.nodes[0].id]
  const adj = new Map<string, string[]>()
  graph.edges.forEach((e) => {
    const list = adj.get(e.source) ?? []
    list.push(e.target)
    adj.set(e.source, list)
  })

  let maxDepth = 0
  for (const root of start) {
    const queue: Array<{ id: string; depth: number }> = [{ id: root, depth: 0 }]
    const seen = new Set<string>()
    while (queue.length) {
      const { id, depth } = queue.shift()!
      if (seen.has(id)) continue
      seen.add(id)
      maxDepth = Math.max(maxDepth, depth)
      for (const next of adj.get(id) ?? []) {
        queue.push({ id: next, depth: depth + 1 })
      }
    }
  }
  return maxDepth
}

function meanConfidence(graph?: EvidenceGraph | null): string {
  if (!graph?.nodes?.length) return '—'
  const vals = graph.nodes
    .map((n) => n.confidence)
    .filter((c): c is number => typeof c === 'number' && !Number.isNaN(c))
  if (!vals.length) return '—'
  const mean = vals.reduce((a, b) => a + b, 0) / vals.length
  return `${(mean * 100).toFixed(0)}%`
}

function clusterSummary(graph?: EvidenceGraph | null): string {
  if (!graph?.nodes?.length) return '—'
  const kinds = new Map<string, number>()
  for (const node of graph.nodes) {
    const k = node.kind ?? 'unknown'
    kinds.set(k, (kinds.get(k) ?? 0) + 1)
  }
  const top = [...kinds.entries()].sort((a, b) => b[1] - a[1]).slice(0, 2)
  return top.map(([k, n]) => `${k}:${n}`).join(' · ') || '—'
}

function defaultWalletId(graph?: EvidenceGraph | null): string | null {
  if (!graph?.nodes?.length) return null
  const wallet =
    graph.nodes.find((n) => n.kind === 'wallet') ??
    graph.nodes.find((n) => /wallet|address/i.test(n.kind))
  return wallet?.id ?? graph.nodes[0]?.id ?? null
}

export const FusionGraphStage = memo(function FusionGraphStage({
  graph,
  loading,
  alerts = [],
  caseRef,
  compact = false,
  live = false,
  livePaused = false,
  persistent = true,
  centerGraphTrigger = 0,
  className,
  crossCaseLinks = [],
  detachHref,
  selectedNodeId,
  onNodeSelect,
  highlightNodeIds = [],
  replayIndex,
  onReplayIndexChange,
  hopLensEnabled = true,
  hopLensMaxDepth: hopLensMaxDepthProp,
  onHopLensMaxDepthChange,
  hopLensOriginId,
  focusNodeId,
  cinematic: cinematicProp,
  onCinematicChange,
  onEvidenceDrop,
  collaborationEnabled = true,
  investigationMode = false,
  initialReactFlowCamera,
  onReactFlowCameraChange,
  initialGpuCamera,
  onGpuCameraChange,
  onGraphDiff,
  onRequestCollect,
  systemsHud,
}: Props) {
  const { announce } = useFusionAnnouncer()
  const graphContainerRef = useRef<HTMLDivElement>(null)
  const autoGpuToastShown = useRef(false)
  const [gpuToggle] = useState(() => isGpuGraphEnabled())
  const [moneyFlowEnabled, setMoneyFlowEnabled] = useState(
    () => getFusionSyncState().moneyFlowEnabled
  )
  const [collabEnabled, setCollabEnabled] = useState(
    () => getFusionSyncState().collaborationEnabled
  )
  const { peers, selfId } = useFusionCollaboration(
    caseRef ?? undefined,
    graphContainerRef,
    (collaborationEnabled ?? collabEnabled) && Boolean(caseRef)
  )
  const [internalHopDepth, setInternalHopDepth] = useState<number | null>(null)
  const [internalCinematic, setInternalCinematic] = useState(false)
  const cinematic = cinematicProp ?? internalCinematic
  const setCinematic = onCinematicChange ?? setInternalCinematic
  const [cameraFocusId, setCameraFocusId] = useState<string | null>(null)
  const [exporting, setExporting] = useState<'png' | 'svg' | null>(null)
  const [exportError, setExportError] = useState<string | null>(null)
  const prevAlertCount = useRef(0)
  const [centerTick, setCenterTick] = useState(centerGraphTrigger)
  const [graphLayers, setGraphLayers] = useState<GraphLayerToggles>(
    () => getFusionSyncState().graphLayers ?? DEFAULT_GRAPH_LAYERS
  )
  const [graphSearchOpen, setGraphSearchOpenState] = useState(
    () => getFusionSyncState().graphSearchOpen
  )
  const [busFocusId, setBusFocusId] = useState<string | null>(
    () => getFusionSyncState().graphFocusNodeId
  )
  const [busFocusTick, setBusFocusTick] = useState(
    () => getFusionSyncState().graphFocusRequest
  )
  const prevGraphRef = useRef<EvidenceGraph | null>(null)
  const [livingNodeIds, setLivingNodeIds] = useState<string[]>([])
  const [diffPulseAlerts, setDiffPulseAlerts] = useState<GraphAlert[]>([])

  useEffect(() => {
    return subscribeFusionSync((sync) => {
      setCenterTick(sync.centerGraphRequest)
      setMoneyFlowEnabled(sync.moneyFlowEnabled)
      setCollabEnabled(sync.collaborationEnabled)
      setGraphLayers(sync.graphLayers)
      setGraphSearchOpenState(sync.graphSearchOpen)
      setBusFocusId(sync.graphFocusNodeId)
      setBusFocusTick(sync.graphFocusRequest)
    })
  }, [])

  useEffect(() => {
    setExecutiveMode(cinematic)
  }, [cinematic])

  useEffect(() => {
    return subscribeFusionSync((sync) => {
      if (!sync.executiveMode && cinematic) {
        setCinematic(false)
      }
    })
  }, [cinematic, setCinematic])

  useEffect(() => {
    setCenterTick(centerGraphTrigger)
  }, [centerGraphTrigger])

  useEffect(() => {
    if (alerts.length > prevAlertCount.current) {
      const newest = alerts[alerts.length - 1]
      announce(`Graph alert: ${newest?.type ?? 'update'}`)
    }
    prevAlertCount.current = alerts.length
  }, [alerts, announce])

  useEffect(() => {
    if (!graph?.nodes?.length) return
    const diffs = diffEvidenceGraphs(prevGraphRef.current, graph)
    if (diffs.length && prevGraphRef.current) {
      onGraphDiff?.(diffs)
      const nodeIds = [...diffNodeIds(diffs)]
      setLivingNodeIds(nodeIds)
      setDiffPulseAlerts(nodeIds.map((nodeId) => ({ nodeId, type: 'graph_diff' })))
      const timer = setTimeout(() => {
        setLivingNodeIds([])
        setDiffPulseAlerts([])
      }, 2800)
      prevGraphRef.current = graph
      return () => clearTimeout(timer)
    }
    prevGraphRef.current = graph
  }, [graph, onGraphDiff])

  const mergedAlerts = useMemo(
    () => [...alerts, ...diffPulseAlerts],
    [alerts, diffPulseAlerts]
  )

  const isLive = live && !livePaused && !getFusionSyncState().livePaused

  const hopLensMaxDepth = hopLensMaxDepthProp ?? internalHopDepth
  const setHopLensMaxDepth = onHopLensMaxDepthChange ?? setInternalHopDepth

  const entityCount = graph?.nodes?.length ?? 0
  const gpuThreshold = investigationMode ? INVESTIGATION_GPU_THRESHOLD : LARGE_GRAPH_THRESHOLD
  const autoGpu = entityCount >= gpuThreshold
  const gpuGraph = gpuToggle || autoGpu

  useEffect(() => {
    if (autoGpu && !autoGpuToastShown.current) {
      autoGpuToastShown.current = true
      toast.info(
        investigationMode
          ? `Investigation graph (${entityCount} nodes) → WebGL mode`
          : 'Large graph → WebGL mode'
      )
    }
  }, [autoGpu, investigationMode, entityCount])
  const hopDepth = useMemo(() => computeHopDepth(graph), [graph])
  const confidence = useMemo(() => meanConfidence(graph), [graph])
  const clusters = useMemo(() => clusterSummary(graph), [graph])

  const lensOrigin =
    hopLensOriginId ?? selectedNodeId ?? defaultWalletId(graph)

  const hopDistances = useMemo(
    () => (hopLensMaxDepth != null ? computeHopDistances(graph, lensOrigin) : null),
    [graph, lensOrigin, hopLensMaxDepth]
  )

  const handleExport = useCallback(
    async (format: 'png' | 'svg') => {
      const container = graphContainerRef.current
      if (!container) {
        const msg = 'Graph not ready'
        setExportError(msg)
        announce(msg, 'assertive')
        toast.error(msg)
        return
      }
      setExporting(format)
      setExportError(null)
      try {
        const stamp = caseRef ?? 'graph'
        await exportGraphSnapshot(container, format, `${stamp}-snapshot.${format}`)
        toast.success(`Exported ${format.toUpperCase()}`)
        announce(`Graph exported as ${format.toUpperCase()}`)
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Export failed'
        setExportError(msg)
        announce(`Export error: ${msg}`, 'assertive')
        toast.error(msg)
      } finally {
        setExporting(null)
      }
    },
    [announce, caseRef]
  )

  return (
    <div
      className={cn(
        'fusion-graph-stage',
        !compact && 'fusion-graph-stage--dominant',
        persistent && 'fusion-graph-stage--persistent',
        isLive && 'fusion-graph-stage--live-breathe',
        className
      )}
    >
      <div className="fusion-graph-hud" aria-hidden="false">
        <div className="fusion-graph-hud__chip">
          <span className="fusion-graph-hud__chip-label">Entities</span>
          <span className="fusion-graph-hud__chip-value">{loading ? '…' : entityCount}</span>
        </div>
        <div className="fusion-graph-hud__chip">
          <span className="fusion-graph-hud__chip-label">Hop Depth</span>
          <span className="fusion-graph-hud__chip-value">{loading ? '…' : hopDepth}</span>
        </div>
        <div className="fusion-graph-hud__chip">
          <span className="fusion-graph-hud__chip-label">Confidence</span>
          <span className="fusion-graph-hud__chip-value">{loading ? '…' : confidence}</span>
        </div>
        {!compact ? (
          <div className="fusion-graph-hud__chip">
            <span className="fusion-graph-hud__chip-label">Clusters</span>
            <span className="fusion-graph-hud__chip-value">{loading ? '…' : clusters}</span>
          </div>
        ) : null}
        {!compact ? (
          <FusionGraphLayerToggles layers={graphLayers} className="pointer-events-auto" />
        ) : null}
        {!compact && hopLensEnabled ? (
          <div className="fusion-graph-hud__chip fusion-graph-hud__chip--interactive">
            <span className="fusion-graph-hud__chip-label">Hop Lens</span>
            <select
              className="fusion-graph-hud__chip-value bg-transparent outline-none"
              value={hopLensMaxDepth ?? ''}
              onChange={(e) => {
                const v = e.target.value
                setHopLensMaxDepth(v === '' ? null : Number(v))
              }}
              aria-label="Hop distance lens"
            >
              <option value="">Off</option>
              {[1, 2, 3, 4, 5].map((d) => (
                <option key={d} value={d}>
                  ≤{d}
                </option>
              ))}
            </select>
          </div>
        ) : null}
        {!compact ? (
          <>
            <FusionCollaborationPresence peers={peers} selfId={selfId} />
            <button
              type="button"
              className="fusion-graph-hud__chip fusion-graph-hud__chip--interactive"
              disabled={Boolean(exporting)}
              onClick={() => void handleExport('png')}
              title="Export graph as PNG"
              aria-label="Export graph as PNG"
            >
              <span className="fusion-graph-hud__chip-label">Export</span>
              <span className="fusion-graph-hud__chip-value">
                {exporting === 'png' ? '…' : 'PNG'}
              </span>
            </button>
            <button
              type="button"
              className="fusion-graph-hud__chip fusion-graph-hud__chip--interactive"
              disabled={Boolean(exporting)}
              onClick={() => void handleExport('svg')}
              title="Export graph as SVG"
              aria-label="Export graph as SVG"
            >
              <span className="fusion-graph-hud__chip-label">Export</span>
              <span className="fusion-graph-hud__chip-value">
                {exporting === 'svg' ? '…' : 'SVG'}
              </span>
            </button>
            {exportError ? (
              <div
                className="fusion-graph-hud__chip fusion-graph-hud__chip--error"
                role="alert"
                title={exportError}
              >
                <span className="fusion-graph-hud__chip-label">Export</span>
                <span className="fusion-graph-hud__chip-value fusion-tone-critical fusion-truncate max-w-[120px]">
                  ERR
                </span>
              </div>
            ) : null}
          </>
        ) : null}
        {!compact ? (
          <FusionCinematicTour
            graph={graph}
            active={cinematic}
            onActiveChange={setCinematic}
            onFocusNode={(id) => {
              setCameraFocusId(id)
              onNodeSelect?.(id)
            }}
            className="pointer-events-auto"
          />
        ) : null}
        <div className="fusion-graph-hud__chip fusion-graph-hud__live" aria-live="polite">
          <span className={cn('fusion-live-dot', isLive && 'fusion-live-dot--active')} aria-hidden />
          <span className="fusion-graph-hud__live-text">{isLive ? 'LIVE' : livePaused ? 'PAUSE' : 'IDLE'}</span>
        </div>
        {detachHref ? (
          <a
            href={detachHref}
            target="_blank"
            rel="noreferrer"
            className="fusion-graph-hud__chip fusion-graph-hud__chip--interactive ml-auto hover:text-[var(--fusion-ops-blue)]"
            title="Open graph in new window"
          >
            <span className="fusion-graph-hud__chip-label">Detach</span>
            <span className="fusion-graph-hud__chip-value">↗</span>
          </a>
        ) : null}
      </div>

      {!compact && graphLayers.crossCase && crossCaseLinks.length > 0 ? (
        <div className="absolute right-2 top-12 z-10 max-w-[220px] rounded-sm border border-[var(--fusion-border)] bg-[var(--fusion-bg-deck)] p-2">
          <p className="fusion-text-micro mb-1">Cross-case links</p>
          <ul className="space-y-1">
            {crossCaseLinks.slice(0, 5).map((link) => (
              <li key={`${link.case_ref}-${link.entity_value}`} className="fusion-text-data truncate">
                <Link
                  to="/dashboard/fusion/investigation/$caseRef"
                  params={{ caseRef: link.case_ref }}
                  className="fusion-mono text-[var(--fusion-ops-blue)]"
                >
                  {link.case_ref}
                </Link>
                <span className="fusion-text-micro ml-1">{link.entity_type}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <FusionGraphSearchPanel
        open={graphSearchOpen}
        graph={graph}
        onSelectNode={onNodeSelect}
      />

      <div ref={graphContainerRef} className="fusion-graph-stage__canvas">
        {loading && !graph?.nodes?.length ? (
          <FusionSkeleton variant="graph" className="absolute inset-0 z-[2]" />
        ) : null}
        {!loading && !graph?.nodes?.length && onRequestCollect ? (
          <FusionEmptyState
            className="absolute inset-0 z-[3] bg-[var(--fusion-bg-void)]"
            title={fusionCopy.graph.awaitingIntelTitle}
            description={fusionCopy.graph.awaitingIntelDescription}
            action={
              <button
                type="button"
                className="fusion-text-micro rounded border border-[var(--fusion-ops-blue)] px-3 py-1.5 text-[var(--fusion-ops-blue)]"
                onClick={onRequestCollect}
              >
                {fusionCopy.graph.collectSeed}
              </button>
            }
          />
        ) : null}
        {gpuGraph ? (
          <FusionGpuGraphView
            graph={graph}
            loading={loading}
            selectedNodeId={selectedNodeId}
            onNodeSelect={onNodeSelect}
            highlightNodeIds={highlightNodeIds}
            focusNodeId={focusNodeId ?? cameraFocusId ?? busFocusId}
            focusGraphRequest={busFocusTick}
            graphLayers={graphLayers}
            alerts={mergedAlerts}
            onEvidenceDrop={onEvidenceDrop}
            moneyFlowEnabled={moneyFlowEnabled}
            readOnly={cinematic}
            initialGpuCamera={initialGpuCamera}
            onGpuCameraChange={onGpuCameraChange}
            className="h-full w-full"
          />
        ) : (
          <ComplianceGraphView
            graph={graph}
            loading={loading}
            alerts={mergedAlerts}
            caseRef={caseRef}
            compact={compact}
            height="100%"
            showHud={false}
            riskPropagation
            selectedNodeId={selectedNodeId}
            onNodeSelect={onNodeSelect}
            highlightNodeIds={highlightNodeIds}
            hopDistances={hopDistances}
            hopLensMaxDepth={hopLensMaxDepth}
            replayIndex={replayIndex}
            onReplayIndexChange={onReplayIndexChange}
            graphContainerRef={graphContainerRef}
            centerGraphTrigger={centerTick}
            focusNodeId={focusNodeId ?? cameraFocusId ?? busFocusId}
            focusGraphRequest={busFocusTick}
            graphLayers={graphLayers}
            onEvidenceDrop={onEvidenceDrop}
            moneyFlowEnabled={moneyFlowEnabled}
            initialViewport={initialReactFlowCamera}
            onViewportChange={onReactFlowCameraChange}
            livingNodeIds={livingNodeIds}
            className="h-full w-full"
          />
        )}
        <FusionCollaborationOverlay peers={peers} />
        {investigationMode && !compact && systemsHud ? (
          <FusionSystemsHud
            scalpelLive={systemsHud.scalpelLive ?? live}
            nodeCount={systemsHud.nodeCount ?? graph?.nodes?.length ?? 0}
            riskLogicOk={systemsHud.riskLogicOk ?? true}
          />
        ) : null}
      </div>
    </div>
  )
})
