import { useEffect, useRef, useState, type RefObject, type CSSProperties } from 'react'

export type CollaboratorCursor = {
  id: string
  x: number
  y: number
  label: string
  color: string
  updatedAt: number
}

type CursorMessage =
  | { type: 'cursor'; source: string; cursor: Omit<CollaboratorCursor, 'updatedAt'> }
  | { type: 'leave'; source: string }

const COLORS = ['#2EC4CF', '#9B7FD4', '#D4A017', '#3BA86B', '#D64545', '#4A8FD4']

function channelName(caseRef: string) {
  return `finskalp-fusion-collab-${caseRef}`
}

export function useFusionCollaboration(
  caseRef: string | undefined,
  containerRef: RefObject<HTMLElement | null>,
  enabled = true
) {
  const sourceId = useRef(
    typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID().slice(0, 8)
      : `a${Date.now() % 10000}`
  )
  const colorRef = useRef(COLORS[Math.floor(Math.random() * COLORS.length)]!)
  const [peers, setPeers] = useState<CollaboratorCursor[]>([])

  useEffect(() => {
    if (!caseRef || !enabled) return
    let channel: BroadcastChannel | null = null
    try {
      channel = new BroadcastChannel(channelName(caseRef))
    } catch {
      return
    }

    const handler = (event: MessageEvent<CursorMessage>) => {
      const data = event.data
      if (!data || data.source === sourceId.current) return
      if (data.type === 'leave') {
        setPeers((prev) => prev.filter((p) => p.id !== data.source))
        return
      }
      if (data.type === 'cursor') {
        setPeers((prev) => {
          const next = prev.filter((p) => p.id !== data.source)
          next.push({ ...data.cursor, id: data.source, updatedAt: Date.now() })
          return next
        })
      }
    }

    channel.addEventListener('message', handler)

    const el = containerRef.current
    if (!el) {
      channel.close()
      return
    }

    let lastSend = 0
    const onMove = (e: MouseEvent) => {
      const now = Date.now()
      if (now - lastSend < 50) return
      lastSend = now
      const rect = el.getBoundingClientRect()
      const x = ((e.clientX - rect.left) / rect.width) * 100
      const y = ((e.clientY - rect.top) / rect.height) * 100
      channel?.postMessage({
        type: 'cursor',
        source: sourceId.current,
        cursor: {
          id: sourceId.current,
          x,
          y,
          label: `Analyst ${sourceId.current.slice(0, 4)}`,
          color: colorRef.current,
        },
      } satisfies CursorMessage)
    }

    el.addEventListener('mousemove', onMove)

    const staleTimer = setInterval(() => {
      const cutoff = Date.now() - 8000
      setPeers((prev) => prev.filter((p) => p.updatedAt > cutoff))
    }, 3000)

    return () => {
      channel?.postMessage({ type: 'leave', source: sourceId.current })
      channel?.removeEventListener('message', handler)
      channel?.close()
      el.removeEventListener('mousemove', onMove)
      clearInterval(staleTimer)
    }
  }, [caseRef, containerRef, enabled])

  return { peers, selfId: sourceId.current }
}

export function FusionCollaborationOverlay({ peers }: { peers: CollaboratorCursor[] }) {
  if (!peers.length) return null
  return (
    <div className="fusion-collab-overlay" aria-hidden>
      {peers.map((p) => (
        <div
          key={p.id}
          className="fusion-collab-cursor"
          style={
            {
              left: `${p.x}%`,
              top: `${p.y}%`,
              '--collab-color': p.color,
            } as CSSProperties
          }
        >
          <span className="fusion-collab-cursor__dot" />
          <span className="fusion-collab-cursor__label">{p.label}</span>
        </div>
      ))}
    </div>
  )
}
