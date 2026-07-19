/** Living graph diff engine — detect new entities, edges, clusters, risk shifts (U2) */

import type { EvidenceGraph } from '@/api/compliance-service'

export type GraphDiffKind =
  | 'node_added'
  | 'edge_added'
  | 'cluster_formed'
  | 'risk_changed'
  | 'node_removed'
  | 'edge_removed'

export type GraphDiffEvent = {
  id: string
  kind: GraphDiffKind
  ts: number
  nodeId?: string
  edgeId?: string
  clusterKind?: string
  clusterCount?: number
  riskDelta?: number
  label?: string
}

function nodeRisk(node: EvidenceGraph['nodes'][number]): number | null {
  const raw = (node as { risk_score?: number; risk?: number }).risk_score ??
    (node as { risk?: number }).risk
  if (typeof raw === 'number' && !Number.isNaN(raw)) return raw
  return null
}

function clusterKey(graph: EvidenceGraph): Map<string, number> {
  const counts = new Map<string, number>()
  for (const node of graph.nodes) {
    const k = node.kind ?? 'unknown'
    counts.set(k, (counts.get(k) ?? 0) + 1)
  }
  return counts
}

export function diffEvidenceGraphs(
  prev: EvidenceGraph | null | undefined,
  next: EvidenceGraph | null | undefined
): GraphDiffEvent[] {
  if (!next?.nodes?.length) return []
  const ts = Date.now()
  const events: GraphDiffEvent[] = []

  const prevNodes = new Map((prev?.nodes ?? []).map((n) => [n.id, n]))
  const nextNodes = new Map(next.nodes.map((n) => [n.id, n]))
  const prevEdges = new Map((prev?.edges ?? []).map((e) => [e.id, e]))
  const nextEdges = new Map((next.edges ?? []).map((e) => [e.id, e]))

  for (const [id, node] of nextNodes) {
    if (!prevNodes.has(id)) {
      events.push({
        id: `node-${id}-${ts}`,
        kind: 'node_added',
        ts,
        nodeId: id,
        label: node.label ?? node.kind ?? id,
      })
    } else {
      const prevRisk = nodeRisk(prevNodes.get(id)!)
      const nextRisk = nodeRisk(node)
      if (prevRisk != null && nextRisk != null && prevRisk !== nextRisk) {
        events.push({
          id: `risk-${id}-${ts}`,
          kind: 'risk_changed',
          ts,
          nodeId: id,
          riskDelta: nextRisk - prevRisk,
          label: node.label ?? id,
        })
      }
    }
  }

  for (const id of prevNodes.keys()) {
    if (!nextNodes.has(id)) {
      events.push({ id: `node-rm-${id}-${ts}`, kind: 'node_removed', ts, nodeId: id })
    }
  }

  for (const [id, edge] of nextEdges) {
    if (!prevEdges.has(id)) {
      events.push({
        id: `edge-${id}-${ts}`,
        kind: 'edge_added',
        ts,
        edgeId: id,
        label: edge.rel_type ?? id,
      })
    }
  }

  for (const id of prevEdges.keys()) {
    if (!nextEdges.has(id)) {
      events.push({ id: `edge-rm-${id}-${ts}`, kind: 'edge_removed', ts, edgeId: id })
    }
  }

  const prevClusters = clusterKey(prev ?? { nodes: [], edges: [] })
  const nextClusters = clusterKey(next)
  for (const [kind, count] of nextClusters) {
    const prevCount = prevClusters.get(kind) ?? 0
    if (count >= 3 && prevCount < 3) {
      events.push({
        id: `cluster-${kind}-${ts}`,
        kind: 'cluster_formed',
        ts,
        clusterKind: kind,
        clusterCount: count,
        label: `${kind} cluster (${count})`,
      })
    }
  }

  return events
}

export function diffNodeIds(events: GraphDiffEvent[]): Set<string> {
  const ids = new Set<string>()
  for (const ev of events) {
    if (ev.nodeId) ids.add(ev.nodeId)
  }
  return ids
}

export function diffEdgeIds(events: GraphDiffEvent[]): Set<string> {
  const ids = new Set<string>()
  for (const ev of events) {
    if (ev.edgeId) ids.add(ev.edgeId)
  }
  return ids
}
