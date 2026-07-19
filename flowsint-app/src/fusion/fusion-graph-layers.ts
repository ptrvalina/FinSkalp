/** Graph HUD layer classification. */

export type GraphLayerToggles = {
  entities: boolean
  transactions: boolean
  evidence: boolean
  crossCase: boolean
}

export const DEFAULT_GRAPH_LAYERS: GraphLayerToggles = {
  entities: true,
  transactions: true,
  evidence: true,
  crossCase: true,
}

export type NodeLayerBucket = 'entity' | 'evidence'

export function classifyNodeLayer(kind: string): NodeLayerBucket {
  const k = kind.toLowerCase()
  if (/evidence|document|report|osint|file|artifact/.test(k)) return 'evidence'
  return 'entity'
}

export function isNodeVisibleForLayers(kind: string, layers: GraphLayerToggles): boolean {
  const bucket = classifyNodeLayer(kind)
  if (bucket === 'evidence') return layers.evidence
  return layers.entities
}

export function isEdgeVisibleForLayers(layers: GraphLayerToggles): boolean {
  return layers.transactions
}
