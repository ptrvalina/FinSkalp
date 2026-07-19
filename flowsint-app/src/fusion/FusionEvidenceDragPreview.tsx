import { useEffect, useState } from 'react'

import { FUSION_EVIDENCE_MIME } from './fusion-evidence-drag'

type Props = {
  containerRef: React.RefObject<HTMLElement | null>
  active?: boolean
}

/** Preview line while dragging evidence toward graph (U6). */
export function FusionEvidenceDragPreview({ containerRef, active = true }: Props) {
  const [line, setLine] = useState<{ x1: number; y1: number; x2: number; y2: number } | null>(
    null
  )

  useEffect(() => {
    if (!active) return

    const onDragOver = (e: DragEvent) => {
      if (!e.dataTransfer?.types.includes(FUSION_EVIDENCE_MIME)) {
        setLine(null)
        return
      }
      const host = containerRef.current
      if (!host) return
      const rect = host.getBoundingClientRect()
      setLine({
        x1: rect.left + rect.width * 0.15,
        y1: rect.top + rect.height * 0.85,
        x2: e.clientX,
        y2: e.clientY,
      })
    }

    const clear = () => setLine(null)

    window.addEventListener('dragover', onDragOver)
    window.addEventListener('drop', clear)
    window.addEventListener('dragend', clear)
    return () => {
      window.removeEventListener('dragover', onDragOver)
      window.removeEventListener('drop', clear)
      window.removeEventListener('dragend', clear)
    }
  }, [active, containerRef])

  if (!line) return null

  return (
    <svg
      className="pointer-events-none fixed inset-0 z-[150]"
      aria-hidden
      width="100%"
      height="100%"
    >
      <line
        x1={line.x1}
        y1={line.y1}
        x2={line.x2}
        y2={line.y2}
        stroke="var(--fusion-ops-blue)"
        strokeWidth={1.5}
        strokeDasharray="6 4"
        opacity={0.75}
      />
      <circle cx={line.x2} cy={line.y2} r={4} fill="var(--fusion-ops-cyan)" opacity={0.9} />
    </svg>
  )
}
