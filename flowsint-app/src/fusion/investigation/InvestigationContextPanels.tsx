import type { RefObject } from 'react'

import { cn } from '@/lib/utils'

import {
  FusionIntelligenceStream,
  resolveTimelineNodeId,
  setEvidenceDragData,
} from '@/fusion'

import { fusionCopy } from '@/fusion/fusion-copy'

import type { InvestigationWorkspace } from './useInvestigationWorkspace'

type TimelineEvent = {
  id: string
  occurred_at: string
  event_type: string
  actor: string
}

type EvidenceItem = {
  id: string
  source_type: string
  content_hash: string
}

type Props = {
  ws: Pick<
    InvestigationWorkspace,
    | 'leftTab'
    | 'setLeftTab'
    | 'setReplayIndex'
    | 'timelineEvents'
    | 'timelineNodeMap'
    | 'graphQuery'
    | 'selectedTimelineEventId'
    | 'handleTimelineEventClick'
    | 'hypotheses'
    | 'evidenceItems'
    | 'selectedEvidenceId'
    | 'handleEvidenceClick'
    | 'selectedNodeId'
  >
  timelineItemRefs: RefObject<Map<string, HTMLLIElement>>
}

export function InvestigationContextPanels({ ws, timelineItemRefs }: Props) {
  const {
    leftTab,
    setLeftTab,
    setReplayIndex,
    timelineEvents,
    timelineNodeMap,
    graphQuery,
    selectedTimelineEventId,
    handleTimelineEventClick,
    hypotheses,
  } = ws

  return (
    <>
      <FusionIntelligenceStream
        className="max-h-[120px] shrink-0 border-b border-[var(--fusion-border)]"
        maxVisible={6}
        onReplayIndex={setReplayIndex}
      />
      <div className="fusion-dock-tabs border-b border-[var(--fusion-border)]">
        {(['timeline', 'hypotheses'] as const).map((tab) => (
          <button
            key={tab}
            type="button"
            className={`fusion-dock-tab ${leftTab === tab ? 'fusion-dock-tab--active' : ''}`}
            onClick={() => setLeftTab(tab)}
          >
            {tab === 'timeline'
              ? fusionCopy.investigation.timelineTab
              : fusionCopy.investigation.hypothesesTab}
          </button>
        ))}
      </div>
      {leftTab === 'timeline' ? (
        <ul className="divide-y divide-[var(--fusion-border)]">
          {timelineEvents.length === 0 ? (
            <li className="fusion-text-micro p-4 text-center">
              {fusionCopy.investigation.awaitingTimeline}
            </li>
          ) : (
            timelineEvents.map((ev: TimelineEvent) => {
              const linkedNodeId =
                timelineNodeMap.get(ev.id) ?? resolveTimelineNodeId(ev, graphQuery.data)
              const isActive = selectedTimelineEventId === ev.id
              return (
                <li
                  key={ev.id}
                  ref={(el) => {
                    if (el) timelineItemRefs.current?.set(ev.id, el)
                    else timelineItemRefs.current?.delete(ev.id)
                  }}
                  className={cn(
                    'fusion-timeline-item px-3 py-2',
                    isActive && 'fusion-timeline-item--active'
                  )}
                  onClick={() => handleTimelineEventClick(ev.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      handleTimelineEventClick(ev.id)
                    }
                  }}
                >
                  <div className="flex gap-2 fusion-text-micro">
                    <span className="fusion-mono shrink-0">
                      {new Date(ev.occurred_at).toLocaleTimeString('ru-RU')}
                    </span>
                    <span>{ev.event_type}</span>
                  </div>
                  <p className="mt-1 fusion-text-data fusion-truncate">{ev.actor}</p>
                  {linkedNodeId ? (
                    <p className="fusion-text-micro mt-0.5 text-[var(--fusion-ops-blue)]">
                      {fusionCopy.investigation.graphNodeLink}
                    </p>
                  ) : null}
                </li>
              )
            })
          )}
        </ul>
      ) : (
        <ul className="divide-y divide-[var(--fusion-border)]">
          {hypotheses.length === 0 ? (
            <li className="fusion-text-micro p-4 text-center">
              {fusionCopy.investigation.noHypotheses}
            </li>
          ) : (
            hypotheses.map((h, i) => (
              <li key={i} className="px-3 py-2 fusion-text-data">
                <p>{h.statement_ru ?? '—'}</p>
                {h.confidence != null ? (
                  <p className="fusion-text-micro mt-1">{Math.round(h.confidence * 100)}%</p>
                ) : null}
              </li>
            ))
          )}
        </ul>
      )}
    </>
  )
}

export function InvestigationEvidencePanel({
  evidenceItems,
  selectedEvidenceId,
  onEvidenceClick,
}: {
  evidenceItems: EvidenceItem[]
  selectedEvidenceId: string | null
  onEvidenceClick: (itemId: string, contentHash: string) => void
}) {
  return (
    <ul className="divide-y divide-[var(--fusion-border)]">
      {evidenceItems.length === 0 ? (
        <li className="fusion-text-micro p-4 text-center">{fusionCopy.investigation.noEvidence}</li>
      ) : (
        evidenceItems.map((item) => (
          <li
            key={item.id}
            className={cn(
              'px-3 py-2 fusion-text-data cursor-pointer',
              selectedEvidenceId === item.id &&
                'bg-[color-mix(in_srgb,var(--fusion-ops-blue)_8%,transparent)]'
            )}
            draggable
            onDragStart={(e) => setEvidenceDragData(e, item.content_hash)}
            onClick={() => onEvidenceClick(item.id, item.content_hash)}
          >
            <span className="fusion-text-micro">{item.source_type}</span>
            <p className="fusion-truncate fusion-mono">{item.content_hash}</p>
          </li>
        ))
      )}
    </ul>
  )
}

export function InvestigationEntityPanel({
  selectedNodeId,
  lastKyt,
  latestRisk,
  nodeLabel,
}: {
  selectedNodeId: string | null
  lastKyt?: { score?: number; level?: string; address?: string } | null
  latestRisk?: { score?: number; source?: string } | null
  nodeLabel?: string | null
}) {
  if (!selectedNodeId) {
    return (
      <p className="fusion-text-micro p-4 text-center text-[var(--fusion-text-tertiary)]">
        {fusionCopy.investigation.selectEntityOnGraph}
      </p>
    )
  }

  const riskScore = lastKyt?.score ?? latestRisk?.score
  const riskLevel = lastKyt?.level ?? latestRisk?.source
  const status =
    riskLevel?.toLowerCase().includes('high') || (riskScore != null && riskScore >= 70)
      ? 'BLOCKED'
      : riskLevel?.toLowerCase().includes('medium')
        ? 'WATCH'
        : 'CLEAR'

  return (
    <div className="fusion-entity-panel p-3">
      <p className="fusion-heading-panel text-[11px] normal-case">
        {nodeLabel ?? fusionCopy.investigation.selectedNode}
      </p>
      <p className="fusion-mono mt-1 break-all text-[11px] text-[var(--fusion-text-tertiary)]">
        {selectedNodeId}
      </p>
      <div className="fusion-stats-grid mt-3">
        <div className="fusion-stats-grid__cell">
          <span className="fusion-stats-grid__label">Total Received</span>
          <span className="fusion-stats-grid__value">—</span>
        </div>
        <div className="fusion-stats-grid__cell">
          <span className="fusion-stats-grid__label">Addresses</span>
          <span className="fusion-stats-grid__value">—</span>
        </div>
        <div className="fusion-stats-grid__cell">
          <span className="fusion-stats-grid__label">Status</span>
          <span
            className={cn(
              'fusion-stats-grid__value',
              status === 'BLOCKED' && 'text-[var(--fusion-ops-red)]',
              status === 'WATCH' && 'text-[var(--fusion-ops-yellow)]',
              status === 'CLEAR' && 'text-[var(--fusion-ops-green)]'
            )}
          >
            {status}
          </span>
        </div>
        <div className="fusion-stats-grid__cell">
          <span className="fusion-stats-grid__label">Risk Score</span>
          <span
            className={cn(
              'fusion-stats-grid__value',
              riskScore != null && riskScore >= 70 && 'text-[var(--fusion-ops-red)]'
            )}
          >
            {riskScore != null ? `${Math.round(riskScore)}/100` : '—'}
          </span>
        </div>
      </div>
      {lastKyt ? (
        <p className="fusion-text-micro mt-2 text-[var(--fusion-text-tertiary)]">
          {fusionCopy.investigation.kytOverlay(lastKyt.score ?? '—', lastKyt.level ?? '—')}
        </p>
      ) : null}
      <div className="mt-3 flex flex-col gap-1">
        <button type="button" className="fusion-text-micro text-left text-[var(--fusion-ops-blue)]">
          Transaction History →
        </button>
        <button type="button" className="fusion-text-micro text-left text-[var(--fusion-ops-blue)]">
          Peer Network →
        </button>
      </div>
    </div>
  )
}
