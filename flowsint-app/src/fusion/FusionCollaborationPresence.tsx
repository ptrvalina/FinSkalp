import type { CollaboratorCursor } from './fusion-collaboration'

type Props = {
  peers: CollaboratorCursor[]
  selfId?: string
}

export function FusionCollaborationPresence({ peers }: Props) {
  const count = peers.length + 1
  if (count <= 1) return null

  return (
    <div className="fusion-graph-hud__chip fusion-collab-presence" title="Live analysts on this case">
      <span className="fusion-graph-hud__chip-label">Analysts</span>
      <span className="fusion-graph-hud__chip-value">{count}</span>
      <span className="fusion-collab-presence__dots" aria-hidden>
        {peers.slice(0, 4).map((p) => (
          <span
            key={p.id}
            className="fusion-collab-presence__dot"
            style={{ background: p.color }}
            title={p.label}
          />
        ))}
      </span>
    </div>
  )
}
