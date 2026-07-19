import Graph from 'graphology'
import type { Attributes } from 'graphology-types'
import type { EvidenceGraph } from '@/api/compliance-service'

/**
 * Auto-enable WebGL when node count exceeds this threshold (perf CI gate: 100k layout <3s).
 * Lowered from 2000 → 1500 per constitution Phase 2 graph excellence target.
 */
export const LARGE_GRAPH_THRESHOLD = 1500

/** Investigation workspace prefers GPU earlier — graph-dominant layout (constitution §Graph OS). */
export const INVESTIGATION_GPU_THRESHOLD = 500

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

export type LodRenderSettings = {
  renderLabels: boolean
  renderEdgeLabels: boolean
  labelSize: number
  nodeSizeScale: number
  edgeSizeScale: number
  hideEdgesOnMove: boolean
}

export type ViewportCamera = {
  x: number
  y: number
  ratio: number
}

export type ViewportReducers = {
  nodeReducer: (node: string, data: Attributes) => Attributes
  edgeReducer: (edge: string, data: Attributes) => Attributes
}

/** Sigma node shape — mirrors ReactFlow FusionEntityNode circle vs rect rules. */
export function gpuNodeTypeForKind(kind?: string | null): 'circle' | 'square' {
  const k = (kind ?? '').toLowerCase()
  if (/exchange|mixer|contract|smart|bank|cex|dex|company|org|evidence|sanction/.test(k)) {
    return 'square'
  }
  return 'circle'
}

export function buildGraphologyFromEvidence(source: EvidenceGraph): Graph {
  const g = new Graph({ multi: false, type: 'directed' })
  for (const node of source.nodes) {
    if (!g.hasNode(node.id)) {
      const k = node.kind?.toLowerCase() ?? 'default'
      g.addNode(node.id, {
        label: node.label,
        kind: node.kind,
        type: gpuNodeTypeForKind(node.kind),
        size: 8 + (node.confidence ?? 0.5) * 6,
        color: KIND_COLOR[k] ?? KIND_COLOR.default,
        x: 0,
        y: 0,
      })
    }
  }
  for (const edge of source.edges) {
    if (g.hasNode(edge.source) && g.hasNode(edge.target) && !g.hasEdge(edge.id)) {
      g.addEdgeWithKey(edge.id, edge.source, edge.target, {
        size: 1 + (edge.strength ?? 0.5) * 3,
        color: '#2A3847',
        label: edge.rel_type,
        strength: edge.strength ?? 0.5,
      })
    }
  }
  return g
}

export function buildSyntheticGraph(nodeCount: number, avgDegree = 4): Graph {
  const g = new Graph({ multi: false, type: 'directed' })
  const kinds = ['wallet', 'address', 'person', 'company', 'exchange', 'evidence']

  for (let i = 0; i < nodeCount; i++) {
    const id = `node-${i}`
    const kind = kinds[i % kinds.length]
    g.addNode(id, {
      label: `Entity ${i}`,
      kind,
      type: gpuNodeTypeForKind(kind),
      size: 10,
      color: KIND_COLOR[kind] ?? KIND_COLOR.default,
      x: 0,
      y: 0,
    })
  }

  const targetEdges = Math.floor((nodeCount * avgDegree) / 2)
  let edgeIdx = 0

  for (let i = 0; i < nodeCount && edgeIdx < targetEdges; i++) {
    const next = (i + 1) % nodeCount
    g.addEdgeWithKey(`edge-ring-${i}`, `node-${i}`, `node-${next}`, {
      size: 2,
      color: '#2A3847',
      label: 'linked',
    })
    edgeIdx++
  }

  for (let i = 0; edgeIdx < targetEdges; i++) {
    const src = i % nodeCount
    const tgt = (src + Math.floor(nodeCount / 3) + (i % 7) + 1) % nodeCount
    if (src === tgt) continue
    const key = `edge-extra-${edgeIdx}`
    if (!g.hasEdge(key)) {
      try {
        g.addEdgeWithKey(key, `node-${src}`, `node-${tgt}`, {
          size: 1.5,
          color: '#2A3847',
          label: 'related',
        })
        edgeIdx++
      } catch {
        /* duplicate edge */
      }
    }
  }

  return g
}

export function applyFastLayout(g: Graph, mode: 'grid' | 'circle'): void {
  const nodes = g.nodes()
  const n = nodes.length
  if (n === 0) return

  if (mode === 'circle') {
    const radius = Math.max(50, Math.sqrt(n) * 8)
    nodes.forEach((id, i) => {
      const angle = (i / n) * Math.PI * 2
      g.setNodeAttribute(id, 'x', Math.cos(angle) * radius)
      g.setNodeAttribute(id, 'y', Math.sin(angle) * radius)
    })
    return
  }

  const cols = Math.ceil(Math.sqrt(n))
  const spacing = 12
  const offset = ((cols - 1) * spacing) / 2
  nodes.forEach((id, i) => {
    const row = Math.floor(i / cols)
    const col = i % cols
    g.setNodeAttribute(id, 'x', col * spacing - offset)
    g.setNodeAttribute(id, 'y', row * spacing - offset)
  })
}

export function getLodRenderSettings(
  nodeCount: number,
  cameraRatio: number
): LodRenderSettings {
  const isLarge = nodeCount >= LARGE_GRAPH_THRESHOLD
  const isHuge = nodeCount >= 10_000
  const zoomedOut = cameraRatio > 1.2

  return {
    renderLabels: !isHuge || cameraRatio < 1.8,
    renderEdgeLabels: nodeCount < 500 && !zoomedOut,
    labelSize: isHuge ? 8 : isLarge ? 9 : 11,
    nodeSizeScale: zoomedOut ? 0.75 : 1,
    edgeSizeScale: zoomedOut ? 0.55 : 1,
    hideEdgesOnMove: isLarge,
  }
}

export function getViewportBounds(
  camera: ViewportCamera,
  containerW: number,
  containerH: number,
  margin = 40
) {
  const halfW = (containerW * camera.ratio) / 2 + margin
  const halfH = (containerH * camera.ratio) / 2 + margin
  return {
    minX: camera.x - halfW,
    maxX: camera.x + halfW,
    minY: camera.y - halfH,
    maxY: camera.y + halfH,
  }
}

export function isNodeInViewport(
  x: number,
  y: number,
  camera: ViewportCamera,
  containerW: number,
  containerH: number,
  margin = 40
): boolean {
  const { minX, maxX, minY, maxY } = getViewportBounds(camera, containerW, containerH, margin)
  return x >= minX && x <= maxX && y >= minY && y <= maxY
}

export function countViewportNodes(
  g: Graph,
  camera: ViewportCamera,
  containerW: number,
  containerH: number,
  margin = 40
): number {
  const { minX, maxX, minY, maxY } = getViewportBounds(camera, containerW, containerH, margin)
  let count = 0
  g.forEachNode((node) => {
    const x = g.getNodeAttribute(node, 'x') as number
    const y = g.getNodeAttribute(node, 'y') as number
    if (x >= minX && x <= maxX && y >= minY && y <= maxY) count++
  })
  return count
}

export function createViewportReducer(
  g: Graph,
  camera: ViewportCamera,
  containerW: number,
  containerH: number,
  margin = 40
): ViewportReducers {
  const { minX, maxX, minY, maxY } = getViewportBounds(camera, containerW, containerH, margin)

  const nodeReducer = (node: string, data: Attributes): Attributes => {
    const x = g.getNodeAttribute(node, 'x') as number
    const y = g.getNodeAttribute(node, 'y') as number
    if (x < minX || x > maxX || y < minY || y > maxY) {
      return { ...data, hidden: true }
    }
    return data
  }

  const edgeReducer = (edge: string, data: Attributes): Attributes => {
    const [src, tgt] = g.extremities(edge)
    const sx = g.getNodeAttribute(src, 'x') as number
    const sy = g.getNodeAttribute(src, 'y') as number
    const tx = g.getNodeAttribute(tgt, 'x') as number
    const ty = g.getNodeAttribute(tgt, 'y') as number
    const srcVis = sx >= minX && sx <= maxX && sy >= minY && sy <= maxY
    const tgtVis = tx >= minX && tx <= maxX && ty >= minY && ty <= maxY
    if (!srcVis && !tgtVis) {
      return { ...data, hidden: true }
    }
    return data
  }

  return { nodeReducer, edgeReducer }
}

export function measureGraphBuildMs(nodeCount: number): number {
  const start = performance.now()
  buildSyntheticGraph(nodeCount)
  return performance.now() - start
}
