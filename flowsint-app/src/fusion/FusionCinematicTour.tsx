import { useCallback, useEffect, useRef, useState } from 'react'
import type { EvidenceGraph } from '@/api/compliance-service'
import { cn } from '@/lib/utils'

type Props = {
  graph?: EvidenceGraph | null
  active: boolean
  onActiveChange: (active: boolean) => void
  onFocusNode: (nodeId: string) => void
  className?: string
}

/** Executive presentation — camera tours high-signal nodes. */
export function FusionCinematicTour({
  graph,
  active,
  onActiveChange,
  onFocusNode,
  className,
}: Props) {
  const [step, setStep] = useState(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const tourNodes = useCallback(() => {
    if (!graph?.nodes?.length) return []
    return [...graph.nodes]
      .sort((a, b) => (b.confidence ?? 0) - (a.confidence ?? 0))
      .slice(0, 12)
      .map((n) => n.id)
  }, [graph])

  useEffect(() => {
    if (!active) {
      if (timerRef.current) clearInterval(timerRef.current)
      setStep(0)
      return
    }
    const ids = tourNodes()
    if (!ids.length) {
      onActiveChange(false)
      return
    }
    onFocusNode(ids[0]!)
    setStep(0)
    timerRef.current = setInterval(() => {
      setStep((s) => {
        const next = (s + 1) % ids.length
        onFocusNode(ids[next]!)
        return next
      })
    }, 3200)
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [active, tourNodes, onFocusNode, onActiveChange])

  if (!graph?.nodes?.length) return null

  const ids = tourNodes()

  return (
    <div
      className={cn(
        'fusion-cinematic-bar',
        active && 'fusion-cinematic-bar--active',
        className
      )}
    >
      <button
        type="button"
        className="fusion-cinematic-bar__btn"
        onClick={() => onActiveChange(!active)}
      >
        {active ? '■ STOP DEMO' : '▶ CINEMATIC'}
      </button>
      {active ? (
        <span className="fusion-cinematic-bar__step">
          {step + 1}/{ids.length} · {graph.nodes.find((n) => n.id === ids[step])?.label ?? ''}
        </span>
      ) : null}
    </div>
  )
}
