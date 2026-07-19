import { Slider } from '@/components/ui/slider'
import { cn } from '@/lib/utils'

import {
  replayIndexForEvent,
  replayStateLabelAtIndex,
  type TimelineEventLike,
} from './fusion-graph-utils'

type Props = {
  replaySteps: number[]
  replayIndex: number
  onReplayIndexChange: (index: number) => void
  timelineEvents?: TimelineEventLike[]
  className?: string
  embedded?: boolean
  playing?: boolean
  onTogglePlay?: () => void
}

function buildTimelineMarkers(
  replaySteps: number[],
  timelineEvents: TimelineEventLike[]
): Array<{ id: string; index: number; label: string }> {
  if (!replaySteps.length || !timelineEvents.length) return []
  const max = replaySteps.length - 1
  const seen = new Set<number>()
  const markers: Array<{ id: string; index: number; label: string }> = []
  for (const ev of timelineEvents) {
    const index = replayIndexForEvent(ev, replaySteps)
    if (seen.has(index)) continue
    seen.add(index)
    markers.push({
      id: ev.id,
      index: Math.min(Math.max(0, index), max),
      label: ev.event_type,
    })
  }
  return markers
}

export function FusionGraphScrubber({
  replaySteps,
  replayIndex,
  onReplayIndexChange,
  timelineEvents = [],
  className,
  embedded = true,
  playing = false,
  onTogglePlay,
}: Props) {
  const hasSteps = replaySteps.length > 1
  const stateLabel = replayStateLabelAtIndex(replaySteps, replayIndex, timelineEvents)
  const ts = replaySteps[Math.min(replayIndex, Math.max(0, replaySteps.length - 1))]
  const markers = buildTimelineMarkers(replaySteps, timelineEvents)

  const markerRail =
    hasSteps && markers.length ? (
      <div className="fusion-graph-scrubber__markers" aria-hidden>
        {markers.map((m) => (
          <button
            key={m.id}
            type="button"
            className="fusion-graph-scrubber__marker"
            style={{ left: `${(m.index / Math.max(1, replaySteps.length - 1)) * 100}%` }}
            title={m.label}
            onClick={() => onReplayIndexChange(m.index)}
          />
        ))}
      </div>
    ) : null

  if (embedded) {
    return (
      <div className={cn('fusion-graph-scrubber', className)} data-testid="fusion-graph-scrubber">
        {onTogglePlay ? (
          <button
            type="button"
            className="fusion-graph-scrubber__play"
            onClick={onTogglePlay}
            aria-label={playing ? 'Pause replay' : 'Play replay'}
          >
            {playing ? '❚❚' : '▶'}
          </button>
        ) : null}
        {hasSteps ? (
          <div className="fusion-graph-scrubber__track-wrap">
            {markerRail}
            <Slider
              className="fusion-graph-scrubber__track"
              min={0}
              max={replaySteps.length - 1}
              step={1}
              value={[replayIndex]}
              onValueChange={([v]) => onReplayIndexChange(v)}
              aria-label="Investigation replay"
            />
          </div>
        ) : (
          <span className="fusion-text-micro flex-1 text-[var(--fusion-text-tertiary)]">
            Awaiting temporal anchors
          </span>
        )}
        <span className="fusion-graph-scrubber__label">{stateLabel}</span>
        {ts ? (
          <span className="fusion-graph-scrubber__label">
            {new Date(ts).toLocaleTimeString('ru-RU')}
          </span>
        ) : null}
      </div>
    )
  }

  return (
    <div
      className={cn(
        'flex flex-col gap-1 border-t border-[var(--fusion-border)] bg-[var(--fusion-bg-panel)] px-2 py-1.5',
        className
      )}
      data-testid="fusion-timeline-scrubber"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="fusion-text-micro text-[var(--fusion-text-tertiary)]">INVESTIGATION REPLAY</span>
        <span className="fusion-text-micro fusion-tone-ops fusion-truncate max-w-[55%]">{stateLabel}</span>
      </div>
      {hasSteps ? (
        <div className="flex items-center gap-2">
          <div className="relative flex-1 min-w-0">
            {markerRail}
            <Slider
              className="w-full"
              min={0}
              max={replaySteps.length - 1}
              step={1}
              value={[replayIndex]}
              onValueChange={([v]) => onReplayIndexChange(v)}
              aria-label="Timeline replay scrubber"
            />
          </div>
          <span className="fusion-mono fusion-text-micro shrink-0 text-[var(--fusion-text-secondary)]">
            {ts ? new Date(ts).toLocaleString('ru-RU') : '—'}
          </span>
        </div>
      ) : (
        <span className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
          No temporal anchors — select timeline events
        </span>
      )}
    </div>
  )
}

/** @deprecated use FusionGraphScrubber */
export const FusionTimelineScrubber = FusionGraphScrubber
