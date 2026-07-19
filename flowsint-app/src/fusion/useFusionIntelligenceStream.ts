import { useEffect, useMemo, useRef } from 'react'

import type { ComplianceLiveEvent } from '@/hooks/use-compliance-events'

import type { GraphDiffEvent } from './fusion-graph-diff'
import {
  pushIntelligenceItem,
  pushIntelligenceItems,
  type IntelligenceStreamItem,
} from './fusion-intelligence-bus'
import type { MioExecutableCard } from './fusion-mio-actions'

type EvidenceItem = {
  id: string
  source_type: string
  content_hash: string
  status?: string
}

type Params = {
  caseRef?: string | null
  liveEvents: ComplianceLiveEvent[]
  mioCards: MioExecutableCard[]
  graphDiffEvents: GraphDiffEvent[]
  evidenceItems: EvidenceItem[]
  enabled?: boolean
}

function severityFromEvent(ev: ComplianceLiveEvent): IntelligenceStreamItem['severity'] {
  const s = (ev.severity ?? '').toLowerCase()
  if (s === 'critical' || s === 'error') return 'critical'
  if (s === 'warning') return 'warning'
  return 'info'
}

function mapSseEvent(ev: ComplianceLiveEvent, caseRef?: string | null): IntelligenceStreamItem {
  const nodeId = String(ev.payload?.address ?? ev.payload?.entity_key ?? '')
  return {
    id: `sse-${ev.id ?? ev.ts ?? Math.random()}`,
    kind: 'sse',
    ts: ev.ts ?? Date.now(),
    title: ev.operator_event_type ?? ev.type ?? 'LIVE EVENT',
    detail: ev.text_ru,
    severity: severityFromEvent(ev),
    nodeId: nodeId || undefined,
    action: nodeId
      ? { type: 'focus_node', nodeId }
      : caseRef
        ? { type: 'open_dock', tab: 'timeline' }
        : undefined,
  }
}

function mapGraphDiff(ev: GraphDiffEvent): IntelligenceStreamItem {
  const severity: IntelligenceStreamItem['severity'] =
    ev.kind === 'risk_changed' ? 'warning' : ev.kind === 'node_added' ? 'info' : 'clear'
  return {
    id: ev.id,
    kind: 'graph_diff',
    ts: ev.ts,
    title:
      ev.kind === 'node_added'
        ? 'NEW ENTITY'
        : ev.kind === 'edge_added'
          ? 'NEW LINK'
          : ev.kind === 'cluster_formed'
            ? 'CLUSTER FORMED'
            : ev.kind === 'risk_changed'
              ? 'RISK SHIFT'
              : ev.kind.toUpperCase(),
    detail: ev.label,
    severity,
    nodeId: ev.nodeId,
    action: ev.nodeId ? { type: 'fly_to', nodeId: ev.nodeId } : undefined,
  }
}

function mapMioCard(card: MioExecutableCard): IntelligenceStreamItem {
  return {
    id: `mio-${card.id}`,
    kind: 'mio',
    ts: Date.now(),
    title: card.title,
    detail: card.rationale,
    severity:
      card.priority === 'critical'
        ? 'critical'
        : card.priority === 'high'
          ? 'warning'
          : 'info',
    action: { type: 'open_dock', tab: 'reports' },
  }
}

function mapEvidence(item: EvidenceItem): IntelligenceStreamItem {
  return {
    id: `evidence-${item.id}`,
    kind: 'evidence',
    ts: Date.now(),
    title: `EVIDENCE · ${item.source_type}`,
    detail: item.content_hash.slice(0, 16),
    severity: 'clear',
    action: { type: 'open_dock', tab: 'evidence' },
  }
}

/** Merge live sources into intelligence stream bus (deduped). */
export function useFusionIntelligenceStream({
  caseRef,
  liveEvents,
  mioCards,
  graphDiffEvents,
  evidenceItems,
  enabled = true,
}: Params): void {
  const seenSse = useRef(new Set<string>())
  const seenDiff = useRef(new Set<string>())
  const seenMio = useRef(new Set<string>())
  const seenEvidence = useRef(new Set<string>())

  useEffect(() => {
    if (!enabled) return
    seenSse.current.clear()
    seenDiff.current.clear()
    seenMio.current.clear()
    seenEvidence.current.clear()
  }, [caseRef, enabled])

  useEffect(() => {
    if (!enabled || !liveEvents.length) return
    const fresh = liveEvents.filter((ev) => {
      const id = `sse-${ev.id ?? ev.ts}`
      if (seenSse.current.has(id)) return false
      seenSse.current.add(id)
      return true
    })
    pushIntelligenceItems(fresh.map((ev) => mapSseEvent(ev, caseRef)))
  }, [liveEvents, caseRef, enabled])

  useEffect(() => {
    if (!enabled || !graphDiffEvents.length) return
    const fresh = graphDiffEvents.filter((ev) => {
      if (seenDiff.current.has(ev.id)) return false
      seenDiff.current.add(ev.id)
      return true
    })
    pushIntelligenceItems(fresh.map(mapGraphDiff))
  }, [graphDiffEvents, enabled])

  useEffect(() => {
    if (!enabled || !mioCards.length) return
    for (const card of mioCards.slice(0, 5)) {
      const id = `mio-${card.id}`
      if (seenMio.current.has(id)) continue
      seenMio.current.add(id)
      pushIntelligenceItem(mapMioCard(card))
    }
  }, [mioCards, enabled])

  useEffect(() => {
    if (!enabled || !evidenceItems.length) return
    for (const item of evidenceItems.slice(0, 8)) {
      const id = `evidence-${item.id}`
      if (seenEvidence.current.has(id)) continue
      seenEvidence.current.add(id)
      pushIntelligenceItem(mapEvidence(item))
    }
  }, [evidenceItems, enabled])
}

export function useIntelligenceStreamPreview(
  liveEvents: ComplianceLiveEvent[],
  mioCards: MioExecutableCard[],
  limit = 3
): IntelligenceStreamItem[] {
  return useMemo(() => {
    const merged: IntelligenceStreamItem[] = [
      ...liveEvents.slice(0, limit).map((ev) => mapSseEvent(ev)),
      ...mioCards.slice(0, 1).map(mapMioCard),
    ]
    return merged.sort((a, b) => b.ts - a.ts).slice(0, limit)
  }, [liveEvents, mioCards, limit])
}
