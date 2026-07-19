import type { EvidenceGraph } from '@/api/compliance-service'

import { fusionCopy } from './fusion-copy'

export type TimelineEventLike = {
  id: string
  event_type: string
  occurred_at: string
  actor: string
  payload?: Record<string, unknown>
}

export function resolveTimelineNodeId(
  event: TimelineEventLike,
  graph?: EvidenceGraph | null
): string | null {
  if (!graph?.nodes?.length) return null

  const actor = (event.actor ?? '').trim().toLowerCase()
  const payload = event.payload ?? {}

  const payloadCandidates = [
    payload.node_id,
    payload.entity_id,
    payload.wallet,
    payload.address,
    payload.target_id,
    payload.source_id,
  ]
    .filter((v): v is string => typeof v === 'string' && v.length > 0)
    .map((v) => v.toLowerCase())

  for (const node of graph.nodes) {
    const id = node.id.toLowerCase()
    const label = (node.label ?? '').toLowerCase()

    if (actor && (id === actor || label.includes(actor) || actor.includes(id))) {
      return node.id
    }

    for (const candidate of payloadCandidates) {
      if (id === candidate || label.includes(candidate)) return node.id
    }
  }

  return null
}

export function buildTimelineNodeMap(
  events: TimelineEventLike[],
  graph?: EvidenceGraph | null
): Map<string, string> {
  const map = new Map<string, string>()
  for (const event of events) {
    const nodeId = resolveTimelineNodeId(event, graph)
    if (nodeId) map.set(event.id, nodeId)
  }
  return map
}

type GraphNodeMeta = {
  timestamp?: string
  ts?: string
}

function collectGraphTimestamps(graph?: EvidenceGraph | null): number[] {
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
  return stamps
}

/** Unified replay scrub steps from graph timestamps + timeline events. */
export function buildReplaySteps(
  graph?: EvidenceGraph | null,
  events: TimelineEventLike[] = []
): number[] {
  const stamps = new Set<number>(collectGraphTimestamps(graph))
  for (const ev of events) {
    const t = new Date(ev.occurred_at).getTime()
    if (!Number.isNaN(t)) stamps.add(t)
  }
  return [...stamps].sort((a, b) => a - b)
}

export function replayIndexForTimestamp(ts: number, steps: number[]): number {
  if (!steps.length) return 0
  let best = 0
  for (let i = 0; i < steps.length; i++) {
    if (steps[i] <= ts) best = i
    else break
  }
  return best
}

export function replayIndexForEvent(
  event: TimelineEventLike,
  steps: number[]
): number {
  const t = new Date(event.occurred_at).getTime()
  if (Number.isNaN(t) || !steps.length) return Math.max(0, steps.length - 1)
  return replayIndexForTimestamp(t, steps)
}

/** Nodes linked to timeline events up to replay cutoff (cumulative highlight). */
export function cumulativeReplayHighlights(
  events: TimelineEventLike[],
  timelineNodeMap: Map<string, string>,
  replayIndex: number,
  replaySteps: number[]
): string[] {
  if (!replaySteps.length) return []
  const cutoff = replaySteps[Math.min(Math.max(0, replayIndex), replaySteps.length - 1)]
  const ids = new Set<string>()
  for (const ev of events) {
    const t = new Date(ev.occurred_at).getTime()
    if (Number.isNaN(t) || t > cutoff) continue
    const nodeId = timelineNodeMap.get(ev.id)
    if (nodeId) ids.add(nodeId)
  }
  return [...ids]
}

export function eventIdAtReplayIndex(
  events: TimelineEventLike[],
  replayIndex: number,
  replaySteps: number[]
): string | null {
  if (!replaySteps.length || !events.length) return null
  const cutoff = replaySteps[Math.min(Math.max(0, replayIndex), replaySteps.length - 1)]
  let last: string | null = null
  for (const ev of events) {
    const t = new Date(ev.occurred_at).getTime()
    if (!Number.isNaN(t) && t <= cutoff) last = ev.id
  }
  return last
}

export function replayCutoffTimestamp(
  replayIndex: number,
  replaySteps: number[]
): number | null {
  if (!replaySteps.length) return null
  return replaySteps[Math.min(Math.max(0, replayIndex), replaySteps.length - 1)] ?? null
}

/** Human-readable investigation state at replay scrub position (U4). */
export function replayStateLabelAtIndex(
  replaySteps: number[],
  replayIndex: number,
  events: TimelineEventLike[] = []
): string {
  if (!replaySteps.length) return fusionCopy.scrubber.noTemporalAnchors
  const cutoff = replayCutoffTimestamp(replayIndex, replaySteps)
  if (cutoff == null) return fusionCopy.scrubber.initialState

  const activeEvents = events.filter((ev) => {
    const t = new Date(ev.occurred_at).getTime()
    return !Number.isNaN(t) && t <= cutoff
  })

  if (!activeEvents.length) {
    return `T+${replayIndex} · ${new Date(cutoff).toLocaleString('ru-RU')}`
  }

  const last = activeEvents[activeEvents.length - 1]!
  const visibleCount = activeEvents.length
  return `${last.event_type} · ${visibleCount} events · ${last.actor.slice(0, 32)}`
}

/** Nearest timeline event for a graph node click (U4 bi-directional). */
export function nearestEventForNode(
  nodeId: string,
  events: TimelineEventLike[],
  timelineNodeMap: Map<string, string>
): TimelineEventLike | null {
  for (const ev of events) {
    if (timelineNodeMap.get(ev.id) === nodeId) return ev
  }
  return null
}

export function computeHopDistances(
  graph: EvidenceGraph | null | undefined,
  originId: string | null
): Map<string, number> | null {
  if (!graph?.nodes?.length || !originId) return null

  const adj = new Map<string, string[]>()
  for (const node of graph.nodes) adj.set(node.id, [])
  for (const edge of graph.edges) {
    adj.get(edge.source)?.push(edge.target)
    adj.get(edge.target)?.push(edge.source)
  }

  if (!adj.has(originId)) return null

  const distances = new Map<string, number>()
  const queue: Array<{ id: string; depth: number }> = [{ id: originId, depth: 0 }]
  const seen = new Set<string>()

  while (queue.length) {
    const { id, depth } = queue.shift()!
    if (seen.has(id)) continue
    seen.add(id)
    distances.set(id, depth)
    for (const next of adj.get(id) ?? []) {
      if (!seen.has(next)) queue.push({ id: next, depth: depth + 1 })
    }
  }

  return distances
}

function loadSvgImage(svgMarkup: string, width: number, height: number): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    const blob = new Blob([svgMarkup], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    img.onload = () => {
      URL.revokeObjectURL(url)
      resolve(img)
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('Failed to render SVG'))
    }
    img.width = width
    img.height = height
    img.src = url
  })
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

export async function exportGraphSnapshot(
  container: HTMLElement,
  format: 'png' | 'svg',
  filename: string
): Promise<void> {
  const pane = container.querySelector('.react-flow') as HTMLElement | null
  if (!pane) throw new Error('Graph not ready')

  const { width, height } = pane.getBoundingClientRect()
  if (width <= 0 || height <= 0) throw new Error('Graph has no dimensions')

  const edgeSvg = pane.querySelector('.react-flow__edges svg') as SVGSVGElement | null
  const nodesLayer = pane.querySelector('.react-flow__nodes') as HTMLElement | null

  if (format === 'svg') {
    const edgeMarkup = edgeSvg
      ? new XMLSerializer().serializeToString(edgeSvg)
      : '<svg xmlns="http://www.w3.org/2000/svg"></svg>'
    const nodesHtml = nodesLayer?.innerHTML ?? ''
    const markup = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}">
<rect width="100%" height="100%" fill="#06080c"/>
<foreignObject width="100%" height="100%">
<div xmlns="http://www.w3.org/1999/xhtml" style="width:${width}px;height:${height}px;position:relative;background:#06080c">
${nodesHtml}
</div>
</foreignObject>
${edgeMarkup.replace(/^<svg[^>]*>/, '').replace(/<\/svg>$/, '')}
</svg>`
    downloadBlob(new Blob([markup], { type: 'image/svg+xml;charset=utf-8' }), filename)
    return
  }

  const canvas = document.createElement('canvas')
  const scale = 2
  canvas.width = Math.ceil(width * scale)
  canvas.height = Math.ceil(height * scale)
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('Canvas unavailable')

  ctx.scale(scale, scale)
  ctx.fillStyle = '#06080c'
  ctx.fillRect(0, 0, width, height)

  const paneRect = pane.getBoundingClientRect()

  if (nodesLayer) {
    for (const nodeEl of nodesLayer.querySelectorAll('.react-flow__node')) {
      const el = nodeEl as HTMLElement
      const rect = el.getBoundingClientRect()
      const x = rect.left - paneRect.left
      const y = rect.top - paneRect.top
      ctx.fillStyle = '#121820'
      ctx.strokeStyle = '#2a3544'
      ctx.lineWidth = 1
      ctx.fillRect(x, y, rect.width, rect.height)
      ctx.strokeRect(x, y, rect.width, rect.height)
      const label = el.textContent?.split('\n')[0]?.trim() ?? el.textContent?.trim() ?? ''
      if (label) {
        ctx.fillStyle = '#e8edf4'
        ctx.font = '11px monospace'
        ctx.fillText(label.slice(0, 28), x + 8, y + 18)
      }
    }
  }

  if (edgeSvg) {
    const svgClone = edgeSvg.cloneNode(true) as SVGSVGElement
    svgClone.setAttribute('width', String(width))
    svgClone.setAttribute('height', String(height))
    const svgMarkup = new XMLSerializer().serializeToString(svgClone)
    const img = await loadSvgImage(svgMarkup, width, height)
    ctx.drawImage(img, 0, 0, width, height)
  }

  const blob = await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('PNG export failed'))), 'image/png')
  })
  downloadBlob(blob, filename)
}
