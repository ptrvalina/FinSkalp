import { memo, useCallback, useEffect, useRef, useState } from 'react'
import Sigma from 'sigma'
import type { EvidenceGraph } from '@/api/compliance-service'
import { cn } from '@/lib/utils'
import {
  applyFastLayout,
  buildGraphologyFromEvidence,
  countViewportNodes,
  createViewportReducer,
  getLodRenderSettings,
} from './fusion-gpu-graph-engine'
import { FusionGpuMoneyFlowOverlay } from './FusionGpuMoneyFlowOverlay'
import {
  DEFAULT_GRAPH_LAYERS,
  isEdgeVisibleForLayers,
  isNodeVisibleForLayers,
  type GraphLayerToggles,
} from './fusion-graph-layers'

type GraphAlert = { nodeId?: string; type?: string }

type Props = {
  graph?: EvidenceGraph | null
  loading?: boolean
  className?: string
  selectedNodeId?: string | null
  onNodeSelect?: (nodeId: string | null) => void
  highlightNodeIds?: string[]
  focusNodeId?: string | null
  focusGraphRequest?: number
  graphLayers?: GraphLayerToggles
  alerts?: GraphAlert[]
  onEvidenceDrop?: (evidenceHash: string, nodeId: string | null) => void
  moneyFlowEnabled?: boolean
  readOnly?: boolean
  initialGpuCamera?: { x: number; y: number; ratio: number }
  onGpuCameraChange?: (camera: { x: number; y: number; ratio: number }) => void
}

const KIND_COLOR: Record<string, string> = {
  wallet: '#2EC4CF',
  address: '#2EC4CF',
  person: '#9B7FD4',
  company: '#4A8FD4',
  exchange: '#D4A017',
  evidence: '#9B7FD4',
  sanction: '#D64545',
  default: '#4A8FD4',
}

const CIRCLE_LAYOUT_THRESHOLD = 500

function applyLodSettings(
  sigma: Sigma,
  nodeCount: number,
  cameraRatio: number
) {
  const lod = getLodRenderSettings(nodeCount, cameraRatio)
  sigma.setSetting('renderLabels', lod.renderLabels)
  sigma.setSetting('renderEdgeLabels', lod.renderEdgeLabels)
  sigma.setSetting('labelSize', lod.labelSize)
  sigma.setSetting('hideEdgesOnMove', lod.hideEdgesOnMove)
  sigma.setSetting('hideLabelsOnMove', lod.hideEdgesOnMove)
  sigma.setSetting('labelRenderedSizeThreshold', lod.renderLabels ? 0 : 999)
}

function applyViewportReducers(
  sigma: Sigma,
  gol: ReturnType<typeof buildGraphologyFromEvidence>,
  containerW: number,
  containerH: number
) {
  const camera = sigma.getCamera()
  const { nodeReducer, edgeReducer } = createViewportReducer(
    gol,
    { x: camera.x, y: camera.y, ratio: camera.ratio },
    containerW,
    containerH
  )
  sigma.setSetting('nodeReducer', nodeReducer)
  sigma.setSetting('edgeReducer', edgeReducer)
}

export const FusionGpuGraphView = memo(function FusionGpuGraphView({
  graph,
  loading,
  className,
  selectedNodeId,
  onNodeSelect,
  highlightNodeIds = [],
  focusNodeId,
  focusGraphRequest = 0,
  graphLayers = DEFAULT_GRAPH_LAYERS,
  alerts = [],
  onEvidenceDrop,
  moneyFlowEnabled = true,
  readOnly = false,
  initialGpuCamera,
  onGpuCameraChange,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const sigmaRef = useRef<Sigma | null>(null)
  const graphRef = useRef<ReturnType<typeof buildGraphologyFromEvidence> | null>(null)
  const cameraSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const onGpuCameraChangeRef = useRef(onGpuCameraChange)
  onGpuCameraChangeRef.current = onGpuCameraChange
  const [perfStats, setPerfStats] = useState({ total: 0, visible: 0 })
  const [dropFlashNodeId, setDropFlashNodeId] = useState<string | null>(null)

  const refreshViewport = useCallback(() => {
    const sigma = sigmaRef.current
    const gol = graphRef.current
    const container = containerRef.current
    if (!sigma || !gol || !container) return

    const w = container.clientWidth || 800
    const h = container.clientHeight || 600
    const camera = sigma.getCamera()

    applyViewportReducers(sigma, gol, w, h)
    applyLodSettings(sigma, gol.order, camera.ratio)
    setPerfStats({
      total: gol.order,
      visible: countViewportNodes(gol, { x: camera.x, y: camera.y, ratio: camera.ratio }, w, h),
    })
    sigma.refresh()
  }, [])

  const mountSigma = useCallback(() => {
    const container = containerRef.current
    if (!container || !graph?.nodes?.length) return

    const gol = buildGraphologyFromEvidence(graph)
    const nodeCount = gol.order
    applyFastLayout(gol, nodeCount < CIRCLE_LAYOUT_THRESHOLD ? 'circle' : 'grid')
    graphRef.current = gol

    if (sigmaRef.current) {
      sigmaRef.current.kill()
      sigmaRef.current = null
    }

    const w = container.clientWidth || 800
    const h = container.clientHeight || 600
    const lod = getLodRenderSettings(nodeCount, 1)

    const sigma = new Sigma(gol, container, {
      renderLabels: lod.renderLabels,
      renderEdgeLabels: lod.renderEdgeLabels,
      labelFont: 'IBM Plex Mono, monospace',
      labelSize: lod.labelSize,
      labelColor: { color: '#ffffff' },
      defaultNodeType: 'circle',
      defaultEdgeType: 'line',
      allowInvalidContainer: false,
      hideEdgesOnMove: lod.hideEdgesOnMove,
      hideLabelsOnMove: lod.hideEdgesOnMove,
      labelRenderedSizeThreshold: lod.renderLabels ? 0 : 999,
    })

    applyViewportReducers(sigma, gol, w, h)
    sigma.on('clickNode', ({ node }) => {
      if (!readOnly) onNodeSelect?.(node)
    })
    sigma.on('clickStage', () => {
      if (!readOnly) onNodeSelect?.(null)
    })

    const camera = sigma.getCamera()
    if (initialGpuCamera) {
      camera.setState(initialGpuCamera)
    }
    camera.on('updated', refreshViewport)
    camera.on('updated', () => {
      if (!onGpuCameraChangeRef.current) return
      if (cameraSaveTimer.current) clearTimeout(cameraSaveTimer.current)
      cameraSaveTimer.current = setTimeout(() => {
        const c = sigma.getCamera()
        onGpuCameraChangeRef.current?.({ x: c.x, y: c.y, ratio: c.ratio })
      }, 280)
    })

    sigmaRef.current = sigma
    setPerfStats({
      total: nodeCount,
      visible: countViewportNodes(gol, { x: camera.x, y: camera.y, ratio: camera.ratio }, w, h),
    })
  }, [graph, onNodeSelect, refreshViewport, readOnly, initialGpuCamera])

  useEffect(() => {
    mountSigma()
    const container = containerRef.current
    if (!container || typeof ResizeObserver === 'undefined') {
      return () => {
        if (cameraSaveTimer.current) clearTimeout(cameraSaveTimer.current)
        const sigma = sigmaRef.current
        if (sigma) sigma.kill()
        sigmaRef.current = null
      }
    }

    const observer = new ResizeObserver(() => {
      const el = containerRef.current
      if (!el || el.clientWidth < 2 || el.clientHeight < 2) return
      if (!sigmaRef.current) mountSigma()
      else refreshViewport()
    })
    observer.observe(container)

    return () => {
      observer.disconnect()
      if (cameraSaveTimer.current) clearTimeout(cameraSaveTimer.current)
      const sigma = sigmaRef.current
      if (sigma) sigma.kill()
      sigmaRef.current = null
    }
  }, [mountSigma, refreshViewport])

  useEffect(() => {
    const gol = graphRef.current
    const sigma = sigmaRef.current
    if (!gol || !sigma) return
    gol.forEachNode((node) => {
      const k = gol.getNodeAttribute(node, 'kind') as string
      const layerVisible = isNodeVisibleForLayers(k ?? '', graphLayers)
      gol.setNodeAttribute(node, 'hidden', !layerVisible)
      const base = KIND_COLOR[k?.toLowerCase()] ?? KIND_COLOR.default
      let color = base
      if (!layerVisible) color = '#333333'
      else if (node === selectedNodeId) color = '#ffffff'
      else if (node === dropFlashNodeId) color = '#D4A017'
      else if (highlightNodeIds.includes(node)) color = '#D4A017'
      if (layerVisible && alerts.some((a) => a.nodeId === node)) color = '#D64545'
      gol.setNodeAttribute(node, 'color', color)
      gol.setNodeAttribute(node, 'size', node === selectedNodeId || node === dropFlashNodeId ? 16 : 10)
    })
    gol.forEachEdge((edge) => {
      gol.setEdgeAttribute(edge, 'hidden', !isEdgeVisibleForLayers(graphLayers))
    })
    sigma.refresh()
  }, [selectedNodeId, highlightNodeIds, alerts, dropFlashNodeId, graphLayers])

  useEffect(() => {
    if (!dropFlashNodeId) return
    const timer = setTimeout(() => setDropFlashNodeId(null), 1600)
    return () => clearTimeout(timer)
  }, [dropFlashNodeId])

  useEffect(() => {
    if (!focusNodeId || !sigmaRef.current || !graphRef.current?.hasNode(focusNodeId)) return
    const attrs = graphRef.current.getNodeAttributes(focusNodeId)
    sigmaRef.current.getCamera().animate({ x: attrs.x, y: attrs.y, ratio: 0.4 }, { duration: 480 })
  }, [focusNodeId, focusGraphRequest])

  const handleDrop = (e: React.DragEvent) => {
    if (readOnly) return
    e.preventDefault()
    const hash = e.dataTransfer.getData('application/fusion-evidence')
    if (!hash || !onEvidenceDrop) return
    const sigma = sigmaRef.current
    if (!sigma) {
      onEvidenceDrop(hash, selectedNodeId ?? null)
      return
    }
    const rect = containerRef.current?.getBoundingClientRect()
    if (!rect) {
      onEvidenceDrop(hash, selectedNodeId ?? null)
      return
    }
    const pos = sigma.viewportToGraph({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    })
    let nearest: string | null = null
    let minD = Infinity
    graphRef.current?.forEachNode((node) => {
      const x = graphRef.current!.getNodeAttribute(node, 'x') as number
      const y = graphRef.current!.getNodeAttribute(node, 'y') as number
      const d = Math.hypot(x - pos.x, y - pos.y)
      if (d < minD) {
        minD = d
        nearest = node
      }
    })
    onEvidenceDrop(hash, nearest)
    if (nearest) {
      setDropFlashNodeId(nearest)
      onNodeSelect?.(nearest)
    }
  }

  if (loading) {
    return (
      <div className={cn('fusion-gpu-graph fusion-gpu-graph--loading', className)}>
        <span className="fusion-text-micro">WebGL · загрузка…</span>
      </div>
    )
  }

  if (!graph?.nodes?.length) {
    return (
      <div className={cn('fusion-gpu-graph fusion-gpu-graph--empty', className)}>
        <span className="fusion-text-micro">WebGL · нет данных графа</span>
      </div>
    )
  }

  return (
    <div className={cn('fusion-gpu-graph', className)}>
      <div
        ref={containerRef}
        className="fusion-gpu-graph__canvas"
        role="application"
        aria-label="WebGL intelligence graph"
        onDragOver={(e) => {
          e.preventDefault()
          e.dataTransfer.dropEffect = 'link'
        }}
        onDrop={handleDrop}
      />
      <FusionGpuMoneyFlowOverlay
        sigmaRef={sigmaRef}
        graphRef={graphRef}
        enabled={moneyFlowEnabled}
      />
      <div className="fusion-gpu-graph__perf-hud" aria-hidden="true">
        <span className="fusion-gpu-graph__perf-badge">WebGL LOD</span>
        <span className="fusion-gpu-graph__perf-stat">
          {perfStats.total.toLocaleString()} nodes
        </span>
        <span className="fusion-gpu-graph__perf-stat">
          {perfStats.visible.toLocaleString()} visible
        </span>
      </div>
    </div>
  )
})
