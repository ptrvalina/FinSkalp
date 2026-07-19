/** @legacy pre-fusion — enhanced with fusion HUD/risk-propagation props */
import { memo, useCallback, useEffect, useMemo, useRef, useState, type DragEvent, type MouseEvent, type RefObject } from 'react'
import {
  Background,
  BaseEdge,
  Controls,
  MiniMap,
  ReactFlow,
  getBezierPath,
  useEdgesState,
  useNodesState,
  type Edge,
  type EdgeProps,
  type Node,
  type NodeTypes,
  type ReactFlowInstance,
} from '@xyflow/react'
import dagre from '@dagrejs/dagre'
import { Bookmark, BookmarkCheck } from 'lucide-react'
import type { EvidenceGraph } from '@/api/compliance-service'
import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import { cn } from '@/lib/utils'
import { FUSION_EVIDENCE_MIME } from '@/fusion/fusion-evidence-drag'
import { FusionEntityNode } from '@/fusion/FusionEntityNode'
import { moneyFlowVisual } from '@/fusion/fusion-money-flow-types'
import {
  DEFAULT_GRAPH_LAYERS,
  isEdgeVisibleForLayers,
  isNodeVisibleForLayers,
  type GraphLayerToggles,
} from '@/fusion/fusion-graph-layers'

type GraphAlert = {
  nodeId?: string
  type?: string
}

type GraphNodeMeta = {
  cluster?: string
  cluster_id?: string
  timestamp?: string
  ts?: string
}

type Props = {
  graph?: EvidenceGraph | null
  loading?: boolean
  height?: number | string
  alerts?: GraphAlert[]
  className?: string
  caseRef?: string | null
  compact?: boolean
  /** Fusion HUD overlay — entity/hop/confidence/live (FusionGraphStage provides external HUD by default) */
  showHud?: boolean
  /** Cascade edge highlight from alert nodes */
  riskPropagation?: boolean
  selectedNodeId?: string | null
  onNodeSelect?: (nodeId: string | null) => void
  highlightNodeIds?: string[]
  hopDistances?: Map<string, number> | null
  hopLensMaxDepth?: number | null
  replayIndex?: number
  onReplayIndexChange?: (index: number) => void
  graphContainerRef?: RefObject<HTMLDivElement | null>
  centerGraphTrigger?: number
  focusNodeId?: string | null
  focusGraphRequest?: number
  graphLayers?: GraphLayerToggles
  onEvidenceDrop?: (evidenceHash: string, nodeId: string | null) => void
  moneyFlowEnabled?: boolean
  initialViewport?: { x: number; y: number; zoom: number }
  onViewportChange?: (viewport: { x: number; y: number; zoom: number }) => void
  livingNodeIds?: string[]
}

const NODE_WIDTH = 190
const NODE_HEIGHT = 72
const PINNED_KEY_PREFIX = 'finskalp-graph-pinned-'

function pinnedStorageKey(caseRef?: string | null) {
  return `${PINNED_KEY_PREFIX}${caseRef ?? 'global'}`
}

function loadPinnedIds(caseRef?: string | null): Set<string> {
  try {
    const raw = localStorage.getItem(pinnedStorageKey(caseRef))
    if (raw) return new Set(JSON.parse(raw) as string[])
  } catch {
    /* ignore */
  }
  return new Set()
}

function savePinnedIds(caseRef: string | null | undefined, ids: Set<string>) {
  try {
    localStorage.setItem(pinnedStorageKey(caseRef), JSON.stringify(Array.from(ids)))
  } catch {
    /* ignore */
  }
}

function nodeDegrees(edges: Edge[]): Map<string, number> {
  const deg = new Map<string, number>()
  for (const e of edges) {
    deg.set(e.source, (deg.get(e.source) ?? 0) + 1)
    deg.set(e.target, (deg.get(e.target) ?? 0) + 1)
  }
  return deg
}

/** Star / hub graphs collapse into a vertical line under dagre LR — use radial layout instead. */
function findLayoutHub(nodes: Node[], edges: Edge[]): string | null {
  if (nodes.length < 4 || edges.length < 3) return null
  const deg = nodeDegrees(edges)
  let hubId: string | null = null
  let maxDeg = 0
  for (const [id, d] of deg) {
    if (d > maxDeg) {
      maxDeg = d
      hubId = id
    }
  }
  if (!hubId || maxDeg < 3) return null
  const neighbors = new Set<string>()
  for (const e of edges) {
    if (e.source === hubId) neighbors.add(e.target)
    if (e.target === hubId) neighbors.add(e.source)
  }
  if (neighbors.size >= Math.max(3, Math.ceil(nodes.length * 0.4))) return hubId
  return null
}

function layoutRadialHub(nodes: Node[], hubId: string): Node[] {
  const satellites = nodes.filter((n) => n.id !== hubId)
  const radius = Math.max(300, Math.min(560, 100 + satellites.length * 24))
  const cx = 420
  const cy = 320
  const positions = new Map<string, { x: number; y: number }>()
  positions.set(hubId, { x: cx - NODE_WIDTH / 2, y: cy - NODE_HEIGHT / 2 })
  satellites.forEach((n, i) => {
    const angle = (2 * Math.PI * i) / satellites.length - Math.PI / 2
    positions.set(n.id, {
      x: cx + radius * Math.cos(angle) - NODE_WIDTH / 2,
      y: cy + radius * Math.sin(angle) - NODE_HEIGHT / 2,
    })
  })
  return nodes.map((n) => ({
    ...n,
    position: positions.get(n.id) ?? n.position,
    style: {
      ...n.style,
      transition: 'transform 400ms ease, opacity 400ms ease',
    },
  }))
}

function layoutGraph(nodes: Node[], edges: Edge[]): Node[] {
  if (!nodes.length) return nodes
  const hubId = findLayoutHub(nodes, edges)
  if (hubId) return layoutRadialHub(nodes, hubId)

  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  const rankdir = nodes.length <= 28 ? 'TB' : 'LR'
  g.setGraph({ rankdir, nodesep: 80, ranksep: 110, marginx: 48, marginy: 48 })
  nodes.forEach((n) => g.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT }))
  edges.forEach((e) => g.setEdge(e.source, e.target))
  dagre.layout(g)
  return nodes.map((n) => {
    const pos = g.node(n.id)
    return {
      ...n,
      position: { x: pos.x - NODE_WIDTH / 2, y: pos.y - NODE_HEIGHT / 2 },
      style: {
        ...n.style,
        transition: 'transform 400ms ease, opacity 400ms ease',
      },
    }
  })
}

function nodeCluster(node: EvidenceGraph['nodes'][number]): string | null {
  const meta = node as EvidenceGraph['nodes'][number] & GraphNodeMeta
  return meta.cluster ?? meta.cluster_id ?? null
}

function graphToFlow(
  graph?: EvidenceGraph | null,
  pinnedIds?: Set<string>,
  showParticles = true
): { nodes: Node[]; edges: Edge[]; clusters: string[] } {
  if (!graph?.nodes?.length) return { nodes: [], edges: [], clusters: [] }

  const clusterSet = new Set<string>()
  graph.nodes.forEach((node) => {
    const c = nodeCluster(node)
    if (c) clusterSet.add(c)
  })

  const nodes: Node[] = graph.nodes.map((node, index) => {
    const cluster = nodeCluster(node)
    if (cluster) clusterSet.add(cluster)
    const isPinned = pinnedIds?.has(node.id)
    return {
      id: node.id,
      type: 'fusionEntity',
      position: { x: 0, y: 0 },
      data: {
        label: node.label,
        index,
        kind: node.kind,
        confidence: node.confidence,
        cluster,
        pinned: isPinned,
      },
      className: cn(
        'compliance-graph-node fusion-entity-node-host',
        isPinned && 'compliance-graph-node--pinned'
      ),
      style: {
        width: NODE_WIDTH,
      },
    }
  })

  const edges: Edge[] = graph.edges.map((edge) => {
    const strength = edge.strength ?? 0.5
    const edgeMeta = edge as typeof edge & GraphNodeMeta
    return {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.rel_type,
      type: 'volume',
      data: {
        volume: strength,
        relType: edge.rel_type,
        timestamp: edgeMeta.timestamp ?? edgeMeta.ts,
        showParticles,
      },
    }
  })

  return { nodes: layoutGraph(nodes, edges), edges, clusters: Array.from(clusterSet) }
}

function collectTimestamps(graph?: EvidenceGraph | null): number[] {
  if (!graph) return []
  const stamps: number[] = []
  for (const node of graph.nodes) {
    const meta = node as typeof node & GraphNodeMeta
    const ts = meta.timestamp ?? meta.ts
    if (ts) {
      const t = new Date(ts).getTime()
      if (!Number.isNaN(t)) stamps.push(t)
    }
  }
  for (const edge of graph.edges) {
    const meta = edge as typeof edge & GraphNodeMeta
    const ts = meta.timestamp ?? meta.ts
    if (ts) {
      const t = new Date(ts).getTime()
      if (!Number.isNaN(t)) stamps.push(t)
    }
  }
  return [...new Set(stamps)].sort((a, b) => a - b)
}

const VolumeEdge = memo(function VolumeEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  markerEnd,
}: EdgeProps) {
  const volume = Number(data?.volume ?? 0.5)
  const hovered = Boolean(data?.hovered)
  const traced = Boolean(data?.traced)
  const relType = String(data?.relType ?? '')
  const flowVisual = moneyFlowVisual(relType)
  const flowColor = flowVisual.color
  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  })
  const strokeWidth = 1 + volume * 3
  const particleCount = Math.max(1, Math.min(6, Math.round(volume * 8)))

  return (
    <>
      {hovered || traced ? (
        <BaseEdge
          id={`${id}-trace`}
          path={edgePath}
          style={{
            stroke: 'var(--fusion-ops-blue)',
            strokeWidth: strokeWidth + 6,
            opacity: traced ? 0.22 : 0.12,
          }}
        />
      ) : null}
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          stroke: hovered || traced ? flowColor : flowColor,
          strokeWidth: traced ? strokeWidth + 1 : strokeWidth,
          strokeDasharray: flowVisual.dash?.join(' '),
          opacity: hovered || traced ? 1 : 0.75,
          transition: 'stroke 200ms ease, stroke-width 200ms ease',
        }}
      />
      {!traced && data?.showParticles !== false
        ? Array.from({ length: particleCount }).map((_, i) => (
            <circle key={`${id}-p-${i}`} r={flowVisual.particleSize + volume} fill={flowColor} opacity={0.85}>
              <animateMotion
                dur={`${Math.max(1.2, 2.8 - volume * 1.5)}s`}
                repeatCount="indefinite"
                path={edgePath}
                begin={`${i * 0.22}s`}
              />
            </circle>
          ))
        : null}
    </>
  )
})

const edgeTypes = { volume: VolumeEdge }
const nodeTypes: NodeTypes = { fusionEntity: FusionEntityNode }

function computeHudMetrics(graph?: EvidenceGraph | null) {
  const entityCount = graph?.nodes?.length ?? 0
  if (!graph?.nodes?.length) {
    return { entityCount: 0, hopDepth: 0, confidence: '—' as string }
  }
  const incoming = new Map<string, number>()
  graph.nodes.forEach((n) => incoming.set(n.id, 0))
  graph.edges.forEach((e) => incoming.set(e.target, (incoming.get(e.target) ?? 0) + 1))
  const roots = graph.nodes.filter((n) => (incoming.get(n.id) ?? 0) === 0).map((n) => n.id)
  const start = roots.length ? roots : [graph.nodes[0].id]
  const adj = new Map<string, string[]>()
  graph.edges.forEach((e) => {
    const list = adj.get(e.source) ?? []
    list.push(e.target)
    adj.set(e.source, list)
  })
  let hopDepth = 0
  for (const root of start) {
    const queue: Array<{ id: string; depth: number }> = [{ id: root, depth: 0 }]
    const seen = new Set<string>()
    while (queue.length) {
      const { id, depth } = queue.shift()!
      if (seen.has(id)) continue
      seen.add(id)
      hopDepth = Math.max(hopDepth, depth)
      for (const next of adj.get(id) ?? []) queue.push({ id: next, depth: depth + 1 })
    }
  }
  const confVals = graph.nodes
    .map((n) => n.confidence)
    .filter((c): c is number => typeof c === 'number' && !Number.isNaN(c))
  const confidence = confVals.length
    ? `${((confVals.reduce((a, b) => a + b, 0) / confVals.length) * 100).toFixed(0)}%`
    : '—'
  return { entityCount, hopDepth, confidence }
}

export function ComplianceGraphView({
  graph,
  loading,
  height = 420,
  alerts = [],
  className,
  caseRef,
  compact = false,
  showHud = false,
  riskPropagation = false,
  selectedNodeId: selectedNodeIdProp,
  onNodeSelect,
  highlightNodeIds = [],
  hopDistances = null,
  hopLensMaxDepth = null,
  replayIndex: replayIndexProp,
  onReplayIndexChange,
  graphContainerRef,
  centerGraphTrigger = 0,
  focusNodeId = null,
  focusGraphRequest = 0,
  graphLayers = DEFAULT_GRAPH_LAYERS,
  onEvidenceDrop,
  moneyFlowEnabled = true,
  initialViewport,
  onViewportChange,
  livingNodeIds = [],
}: Props) {
  const [pinnedIds, setPinnedIds] = useState<Set<string>>(() => loadPinnedIds(caseRef))
  const rfInstance = useRef<ReactFlowInstance | null>(null)
  const initial = useMemo(
    () => graphToFlow(graph, pinnedIds, moneyFlowEnabled),
    [graph, pinnedIds, moneyFlowEnabled]
  )
  const [nodes, setNodes, onNodesChange] = useNodesState(initial.nodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initial.edges)
  const [hoveredEdgeId, setHoveredEdgeId] = useState<string | null>(null)
  const [internalSelectedNodeId, setInternalSelectedNodeId] = useState<string | null>(null)
  const [internalReplayIndex, setInternalReplayIndex] = useState(0)
  const [dropFlashNodeId, setDropFlashNodeId] = useState<string | null>(null)
  const propagateTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const internalContainerRef = useRef<HTMLDivElement>(null)

  const selectedNodeId = selectedNodeIdProp ?? internalSelectedNodeId
  const replayIndex = replayIndexProp ?? internalReplayIndex
  const setReplayIndex = onReplayIndexChange ?? setInternalReplayIndex
  const containerRef = graphContainerRef ?? internalContainerRef
  const highlightKey = highlightNodeIds.join('\0')
  const livingKey = livingNodeIds.join('\0')
  const highlightSet = useMemo(
    () => new Set(highlightNodeIds),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- stabilize by content, not array identity
    [highlightKey]
  )
  const livingSet = useMemo(
    () => new Set(livingNodeIds),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- stabilize by content, not array identity
    [livingKey]
  )
  const viewportRestored = useRef(false)

  const timestamps = useMemo(() => collectTimestamps(graph), [graph])
  const hudMetrics = useMemo(() => computeHudMetrics(graph), [graph])
  const hasTemporal = timestamps.length > 1
  const clusters = initial.clusters

  useEffect(() => {
    setPinnedIds(loadPinnedIds(caseRef))
  }, [caseRef])

  useEffect(() => {
    if (!centerGraphTrigger || !rfInstance.current) return
    void rfInstance.current.fitView({ padding: compact ? 0.35 : 0.2, duration: 400 })
  }, [centerGraphTrigger, compact])

  useEffect(() => {
    if (!focusNodeId || !rfInstance.current) return
    const node = rfInstance.current.getNode(focusNodeId)
    if (!node) return
    void rfInstance.current.setCenter(
      node.position.x + NODE_WIDTH / 2,
      node.position.y + NODE_HEIGHT / 2,
      { zoom: 1.15, duration: 480 }
    )
  }, [focusNodeId, focusGraphRequest])

  useEffect(() => {
    if (!initialViewport || !rfInstance.current || viewportRestored.current) return
    rfInstance.current.setViewport(initialViewport, { duration: 0 })
    viewportRestored.current = true
  }, [initialViewport, nodes.length])

  useEffect(() => {
    const next = graphToFlow(graph, pinnedIds, moneyFlowEnabled)
    setNodes(next.nodes)
    setEdges(next.edges)
    if (replayIndexProp == null) {
      setInternalReplayIndex(timestamps.length > 0 ? timestamps.length - 1 : 0)
    }
  }, [graph, pinnedIds, moneyFlowEnabled, setNodes, setEdges, timestamps.length, replayIndexProp])

  useEffect(() => {
    if (!rfInstance.current || !graph?.nodes?.length) return
    const timer = window.setTimeout(() => {
      void rfInstance.current?.fitView({ padding: compact ? 0.28 : 0.18, duration: 350, maxZoom: 1.25 })
    }, 80)
    return () => window.clearTimeout(timer)
  }, [graph, compact])

  useEffect(() => {
    setNodes((prev) =>
      prev.map((n) => {
        const hopDepth = hopDistances?.get(n.id)
        const withinHopLens =
          hopLensMaxDepth == null ||
          hopDistances == null ||
          hopDepth == null ||
          hopDepth <= hopLensMaxDepth
        const isSelected = selectedNodeId === n.id
        const isTimelineFocus = highlightSet.has(n.id)
        const isDropFlash = dropFlashNodeId === n.id
        return {
          ...n,
          className: cn(
            'compliance-graph-node',
            pinnedIds.has(n.id) && 'compliance-graph-node--pinned',
            isSelected && 'compliance-graph-node--selected',
            isTimelineFocus && 'compliance-graph-node--timeline-focus',
            isDropFlash && 'compliance-graph-node--replay-active',
            livingSet.has(n.id) && 'fusion-animate-entity-pulse compliance-graph-node--alert',
            !withinHopLens && 'compliance-graph-node--hop-dim'
          ),
          style: {
            ...n.style,
            opacity: withinHopLens ? (n.style?.opacity ?? 1) : 0.22,
          },
        }
      })
    )
    setEdges((prev) =>
      prev.map((e) => {
        if (hopLensMaxDepth == null || !hopDistances) return e
        const sourceDepth = hopDistances.get(e.source)
        const targetDepth = hopDistances.get(e.target)
        const visible =
          sourceDepth != null &&
          targetDepth != null &&
          sourceDepth <= hopLensMaxDepth &&
          targetDepth <= hopLensMaxDepth
        return {
          ...e,
          style: {
            ...e.style,
            opacity: visible ? 1 : 0.12,
          },
        }
      })
    )
  }, [
    selectedNodeId,
    highlightSet,
    hopDistances,
    hopLensMaxDepth,
    pinnedIds,
    setNodes,
    setEdges,
    dropFlashNodeId,
  ])

  useEffect(() => {
    if (!alerts.length) return
    const pulseIds = new Set(alerts.map((a) => a.nodeId).filter(Boolean) as string[])
    setNodes((prev) =>
      prev.map((n) => ({
        ...n,
        className: cn(
          'compliance-graph-node',
          pulseIds.has(n.id) && 'compliance-graph-node--alert',
          riskPropagation && pulseIds.has(n.id) && 'compliance-graph-node--fusion-propagate',
          pinnedIds.has(n.id) && 'compliance-graph-node--pinned'
        ),
      }))
    )

    if (!riskPropagation || !graph?.edges?.length) return

    const seedIds = [...pulseIds]
    if (!seedIds.length) return

    const adj = new Map<string, Array<{ target: string; edgeId: string }>>()
    graph.edges.forEach((e) => {
      const list = adj.get(e.source) ?? []
      list.push({ target: e.target, edgeId: e.id })
      adj.set(e.source, list)
    })

    const visited = new Set<string>(seedIds)
    const edgeWaves: string[][] = []
    let frontier = seedIds
    for (let depth = 0; depth < 2 && frontier.length; depth++) {
      const wave: string[] = []
      const next: string[] = []
      for (const nodeId of frontier) {
        for (const { target, edgeId } of adj.get(nodeId) ?? []) {
          wave.push(edgeId)
          if (!visited.has(target)) {
            visited.add(target)
            next.push(target)
          }
        }
      }
      if (wave.length) edgeWaves.push(wave)
      frontier = next
    }

    const connected = new Set(seedIds)
    visited.forEach((id) => connected.add(id))

    if (propagateTimer.current) clearTimeout(propagateTimer.current)

    setNodes((prev) =>
      prev.map((n) => ({
        ...n,
        style: {
          ...n.style,
          opacity: connected.has(n.id) ? 1 : 0.35,
        },
      }))
    )

    edgeWaves.forEach((wave, waveIndex) => {
      setTimeout(() => {
        setEdges((prev) =>
          prev.map((e) => ({
            ...e,
            data: {
              ...e.data,
              traced: wave.includes(e.id) || Boolean(e.data?.traced),
            },
            className: wave.includes(e.id) ? 'compliance-graph-edge--cascade' : e.className,
          }))
        )
      }, waveIndex * 200)
    })

    propagateTimer.current = setTimeout(() => {
      setEdges((prev) =>
        prev.map((e) => ({
          ...e,
          data: { ...e.data, traced: false, hovered: false },
          className: undefined,
        }))
      )
      setNodes((prev) =>
        prev.map((n) => ({
          ...n,
          style: { ...n.style, opacity: 1 },
          className: cn(
            'compliance-graph-node',
            pulseIds.has(n.id) && 'compliance-graph-node--alert',
            pinnedIds.has(n.id) && 'compliance-graph-node--pinned'
          ),
        }))
      )
    }, edgeWaves.length * 200 + 3000)

    return () => {
      if (propagateTimer.current) clearTimeout(propagateTimer.current)
    }
  }, [alerts, pinnedIds, setNodes, setEdges, riskPropagation, graph?.edges])

  const togglePin = useCallback(
    (nodeId: string) => {
      setPinnedIds((prev) => {
        const next = new Set(prev)
        if (next.has(nodeId)) next.delete(nodeId)
        else next.add(nodeId)
        savePinnedIds(caseRef, next)
        return next
      })
    },
    [caseRef]
  )

  const tracePath = useCallback(
    (edgeId: string | null) => {
      if (!edgeId) {
        setEdges((prev) =>
          prev.map((e) => ({ ...e, data: { ...e.data, hovered: false, traced: false } }))
        )
        setNodes((prev) =>
          prev.map((n) => ({
            ...n,
            style: { ...n.style, opacity: 1 },
          }))
        )
        return
      }
      const edge = edges.find((e) => e.id === edgeId)
      if (!edge) return
      const connected = new Set([edge.source, edge.target])
      setEdges((prev) =>
        prev.map((e) => {
          const onPath = e.source === edge.source || e.target === edge.target || e.id === edgeId
          return {
            ...e,
            data: {
              ...e.data,
              hovered: e.id === edgeId,
              traced: onPath,
            },
          }
        })
      )
      setNodes((prev) =>
        prev.map((n) => ({
          ...n,
          style: {
            ...n.style,
            opacity: connected.has(n.id) ? 1 : 0.35,
          },
        }))
      )
    },
    [edges, setEdges, setNodes]
  )

  const onEdgeMouseEnter = useCallback(
    (_: MouseEvent, edge: Edge) => {
      setHoveredEdgeId(edge.id)
      tracePath(edge.id)
    },
    [tracePath]
  )

  const onEdgeMouseLeave = useCallback(() => {
    setHoveredEdgeId(null)
    tracePath(null)
  }, [tracePath])

  const onNodeClick = useCallback(
    (_: MouseEvent, node: Node) => {
      if (onNodeSelect) {
        onNodeSelect(node.id)
      } else {
        setInternalSelectedNodeId(node.id)
      }
    },
    [onNodeSelect]
  )

  const onNodeDoubleClick = useCallback(
    (_: MouseEvent, node: Node) => {
      togglePin(node.id)
    },
    [togglePin]
  )

  const handleEvidenceDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault()
      const hash = e.dataTransfer.getData(FUSION_EVIDENCE_MIME)
      if (!hash || !onEvidenceDrop) return
      const inst = rfInstance.current
      if (!inst) {
        onEvidenceDrop(hash, selectedNodeId ?? null)
        return
      }
      const pos = inst.screenToFlowPosition({ x: e.clientX, y: e.clientY })
      let nearest: string | null = null
      let minD = Infinity
      for (const n of nodes) {
        if (n.hidden) continue
        const nx = n.position.x + NODE_WIDTH / 2
        const ny = n.position.y + NODE_HEIGHT / 2
        const d = Math.hypot(nx - pos.x, ny - pos.y)
        if (d < minD) {
          minD = d
          nearest = n.id
        }
      }
      onEvidenceDrop(hash, nearest)
      if (nearest) {
        setDropFlashNodeId(nearest)
        onNodeSelect?.(nearest)
        setTimeout(() => setDropFlashNodeId(null), 1600)
      }
    },
    [nodes, onEvidenceDrop, onNodeSelect, selectedNodeId]
  )

  const handleEvidenceDragOver = useCallback((e: DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'link'
  }, [])

  useEffect(() => {
    if (!hasTemporal || !timestamps.length) {
      setNodes((prev) =>
        prev.map((n) => {
          const kind = String(n.data?.kind ?? '')
          const layerVisible = isNodeVisibleForLayers(kind, graphLayers)
          return {
            ...n,
            hidden: !layerVisible,
          }
        })
      )
      setEdges((prev) =>
        prev.map((e) => ({
          ...e,
          hidden: !isEdgeVisibleForLayers(graphLayers),
        }))
      )
      return
    }
    const cutoff = timestamps[Math.min(replayIndex, timestamps.length - 1)]
    setNodes((prev) =>
      prev.map((n) => {
        const meta = graph?.nodes.find((gn) => gn.id === n.id) as GraphNodeMeta | undefined
        const ts = meta?.timestamp ?? meta?.ts
        const t = ts ? new Date(ts).getTime() : null
        const temporalVisible = t == null || t <= cutoff
        const replayActive = t != null && t <= cutoff
        const kind = String(n.data?.kind ?? graph?.nodes.find((gn) => gn.id === n.id)?.kind ?? '')
        const layerVisible = isNodeVisibleForLayers(kind, graphLayers)
        return {
          ...n,
          hidden: !(layerVisible && temporalVisible),
          className: cn(
            n.className,
            replayActive && 'compliance-graph-node--replay-active'
          ),
        }
      })
    )
    setEdges((prev) =>
      prev.map((e) => {
        const edgeMeta = graph?.edges.find((ge) => ge.id === e.id) as GraphNodeMeta | undefined
        const ts = edgeMeta?.timestamp ?? edgeMeta?.ts ?? (e.data as GraphNodeMeta | undefined)?.timestamp ?? (e.data as GraphNodeMeta | undefined)?.ts
        const t = ts ? new Date(ts).getTime() : null
        const temporalVisible = t == null || t <= cutoff
        const replayActive = t != null && t <= cutoff
        const layerVisible = isEdgeVisibleForLayers(graphLayers)
        return {
          ...e,
          hidden: !(layerVisible && temporalVisible),
          data: { ...e.data, replayActive },
          className: cn(e.className, replayActive && 'compliance-graph-edge--replay-active'),
        }
      })
    )
  }, [replayIndex, hasTemporal, timestamps, graph, graphLayers, setNodes, setEdges])

  if (loading) {
    return (
      <div
        className={className}
        style={{ height }}
        aria-busy="true"
        aria-label="Loading graph"
      />
    )
  }

  if (!nodes.length) {
    return (
      <div
        className={`flex items-center justify-center text-sm text-[var(--fusion-text-secondary)] ${className ?? ''}`}
        style={{ height }}
      >
        No graph data yet.
      </div>
    )
  }

  const pinnedList = nodes.filter((n) => pinnedIds.has(n.id))

  return (
    <div
      ref={containerRef}
      className={cn('relative', className)}
      style={{ height }}
      onDragOver={onEvidenceDrop ? handleEvidenceDragOver : undefined}
      onDrop={onEvidenceDrop ? handleEvidenceDrop : undefined}
    >
      <style>{`
        @keyframes complianceNodeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes complianceKytPulse {
          0%, 100% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.35); }
          50% { box-shadow: 0 0 0 6px rgba(220, 38, 38, 0); }
        }
        .compliance-graph-node--alert {
          animation: complianceKytPulse 1.6s ease-in-out infinite !important;
          border-color: rgb(220, 38, 38) !important;
        }
        .compliance-graph-node--pinned {
          border-color: var(--fusion-ops-blue) !important;
        }
        .compliance-graph-node--replay-active {
          box-shadow: 0 0 0 2px color-mix(in srgb, var(--fusion-ops-yellow) 45%, transparent) !important;
        }
        .compliance-graph-edge--replay-active {
          opacity: 1 !important;
        }
      `}</style>

      {showHud ? (
        <div className="fusion-graph-hud" style={{ zIndex: 10 }}>
          <div className="fusion-graph-hud__chip">
            <span className="fusion-graph-hud__chip-label">Entities</span>
            <span className="fusion-graph-hud__chip-value">{hudMetrics.entityCount}</span>
          </div>
          <div className="fusion-graph-hud__chip">
            <span className="fusion-graph-hud__chip-label">Hop Depth</span>
            <span className="fusion-graph-hud__chip-value">{hudMetrics.hopDepth}</span>
          </div>
          <div className="fusion-graph-hud__chip">
            <span className="fusion-graph-hud__chip-label">Confidence</span>
            <span className="fusion-graph-hud__chip-value">{hudMetrics.confidence}</span>
          </div>
        </div>
      ) : null}

      {!compact && clusters.length > 0 ? (
        <div className="absolute left-2 top-2 z-10 flex max-w-[60%] flex-wrap gap-1">
          {clusters.map((c) => (
            <span
              key={c}
              className="rounded-sm border border-[var(--fusion-border)] bg-[var(--fusion-bg-panel)] px-1.5 py-0.5 text-[9px] text-[var(--fusion-text-secondary)]"
            >
              ⬡ {c}
            </span>
          ))}
        </div>
      ) : null}

      {!compact && pinnedList.length > 0 ? (
        <div className="absolute right-2 top-2 z-10 max-w-[200px] rounded-sm border border-[var(--fusion-border)] bg-[var(--fusion-bg-panel)] p-2">
          <p className="mb-1 text-[9px] uppercase tracking-wider text-[var(--fusion-text-tertiary)]">
            Pinned
          </p>
          <ul className="space-y-1">
            {pinnedList.map((n) => (
              <li key={n.id} className="flex items-center justify-between gap-1 text-[10px]">
                <span className="truncate">{String(n.data.label).split('\n')[0]}</span>
                <button
                  type="button"
                  className="shrink-0 text-[var(--fusion-ops-blue)]"
                  onClick={() => togglePin(n.id)}
                  aria-label="Unpin node"
                >
                  <BookmarkCheck className="h-3 w-3" />
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onInit={(inst) => {
          rfInstance.current = inst
        }}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        edgeTypes={edgeTypes}
        nodeTypes={nodeTypes}
        onEdgeMouseEnter={onEdgeMouseEnter}
        onEdgeMouseLeave={onEdgeMouseLeave}
        onNodeClick={onNodeClick}
        onNodeDoubleClick={onNodeDoubleClick}
        onMoveEnd={(_, viewport) => onViewportChange?.(viewport)}
        fitView={!initialViewport}
        fitViewOptions={{ padding: compact ? 0.35 : 0.2 }}
        minZoom={0.15}
        maxZoom={1.8}
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={16} size={1} color="var(--fusion-border)" />
        {!compact ? (
          <MiniMap
            nodeStrokeWidth={2}
            pannable
            zoomable
            style={{ background: 'var(--fusion-bg-deck)' }}
          />
        ) : null}
        {!compact ? <Controls showInteractive={false} /> : null}
      </ReactFlow>

      {!compact ? (
        <div className="absolute bottom-2 left-2 right-2 flex flex-wrap items-center gap-2 rounded-sm border border-[var(--fusion-border)] bg-[var(--fusion-bg-panel)] px-2 py-1.5">
          <span className="text-[10px] text-[var(--fusion-text-tertiary)]">Temporal replay</span>
          {hasTemporal ? (
            <>
              <Slider
                className="max-w-[200px] flex-1"
                min={0}
                max={timestamps.length - 1}
                step={1}
                value={[replayIndex]}
                onValueChange={([v]) => setReplayIndex(v)}
              />
              <span className="font-mono text-[10px] text-[var(--fusion-text-secondary)]">
                {new Date(timestamps[replayIndex]).toLocaleString('ru-RU')}
              </span>
            </>
          ) : (
            <span className="text-[10px] text-[var(--fusion-text-tertiary)]">
              No temporal data on graph edges/nodes
            </span>
          )}
          {selectedNodeId ? (
            <Button
              size="sm"
              variant="ghost"
              className="ml-auto h-6 gap-1 px-2 text-[10px]"
              onClick={() => togglePin(selectedNodeId)}
            >
              {pinnedIds.has(selectedNodeId) ? (
                <BookmarkCheck className="h-3 w-3" />
              ) : (
                <Bookmark className="h-3 w-3" />
              )}
              {pinnedIds.has(selectedNodeId) ? 'Unpin' : 'Pin node'}
            </Button>
          ) : null}
        </div>
      ) : null}

      {hoveredEdgeId ? (
        <div className="pointer-events-none absolute bottom-12 left-2 rounded-sm border border-[var(--fusion-border)] bg-[var(--fusion-bg-panel)] px-2 py-1 text-[10px] text-[var(--fusion-text-secondary)]">
          Path trace · source → target
        </div>
      ) : null}
    </div>
  )
}
