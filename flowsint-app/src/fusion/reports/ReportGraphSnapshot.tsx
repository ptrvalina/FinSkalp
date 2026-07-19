import { useMemo } from 'react'

import type { ReportCaseBundle } from './report-types'
import { reportEdges, reportNodes, shortEntityLabel } from './report-intel'

type Pos = { x: number; y: number }

function layoutRadial(
  nodeIds: string[],
  edges: Array<{ source: string; target: string }>,
  width: number,
  height: number
): Map<string, Pos> {
  const pos = new Map<string, Pos>()
  if (!nodeIds.length) return pos

  const deg = new Map<string, number>()
  for (const id of nodeIds) deg.set(id, 0)
  for (const e of edges) {
    if (deg.has(e.source)) deg.set(e.source, (deg.get(e.source) ?? 0) + 1)
    if (deg.has(e.target)) deg.set(e.target, (deg.get(e.target) ?? 0) + 1)
  }

  let hub = nodeIds[0]
  let best = -1
  for (const [id, d] of deg) {
    if (d > best) {
      best = d
      hub = id
    }
  }

  const cx = width / 2
  const cy = height / 2
  pos.set(hub, { x: cx, y: cy })

  const satellites = nodeIds.filter((id) => id !== hub)
  const radius = Math.min(width, height) * 0.38
  satellites.forEach((id, i) => {
    const angle = (2 * Math.PI * i) / Math.max(satellites.length, 1) - Math.PI / 2
    pos.set(id, {
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle),
    })
  })
  return pos
}

function kindColor(kind?: string, node?: { sanctioned?: boolean; scam?: boolean; label?: string; flags?: string[] }): string {
  if (node?.sanctioned || (node?.flags ?? []).includes('sanctioned') || /SANCTION/i.test(node?.label ?? '')) {
    return '#ff4d4f'
  }
  if (node?.scam || (node?.flags ?? []).includes('scam') || /SCAM/i.test(node?.label ?? '')) {
    return '#ff9f43'
  }
  const k = (kind ?? '').toLowerCase()
  if (k.includes('registry')) return '#ff6b6b'
  if (k.includes('wallet')) return '#2ec4cf'
  if (k.includes('osint') || k.includes('mention')) return '#afc6ff'
  if (k.includes('platform') || k.includes('subject')) return '#d8baff'
  if (k.includes('tx') || k.includes('transfer')) return '#67df70'
  return '#8c90a0'
}

export function ReportGraphSnapshot({
  bundle,
  height = 280,
}: {
  bundle: ReportCaseBundle
  height?: number
}) {
  const nodes = reportNodes(bundle)
  const edges = reportEdges(bundle)
  const width = 640

  const positions = useMemo(
    () =>
      layoutRadial(
        nodes.map((n) => n.id),
        edges,
        width,
        height
      ),
    [nodes, edges, height]
  )

  if (!nodes.length) {
    return (
      <p className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
        Нет узлов графа — запустите Collect / Scalpel.
      </p>
    )
  }

  const byId = new Map(nodes.map((n) => [n.id, n]))

  return (
    <div className="fusion-report-doc__graph-viz" data-testid="fusion-report-graph-snapshot">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`Граф: ${nodes.length} узлов, ${edges.length} связей`}>
        <defs>
          <marker
            id="report-edge-arrow"
            viewBox="0 0 10 10"
            refX="8"
            refY="5"
            markerWidth="5"
            markerHeight="5"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(46,196,207,0.55)" />
          </marker>
        </defs>

        {edges.map((e) => {
          const a = positions.get(e.source)
          const b = positions.get(e.target)
          if (!a || !b) return null
          const flagged = /SANCTION|SCAM/i.test(e.rel_type ?? '')
          return (
            <line
              key={e.id}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke={flagged ? 'rgba(255,77,79,0.85)' : 'rgba(46,196,207,0.55)'}
              strokeWidth={flagged ? 2.2 : 1.5}
              markerEnd="url(#report-edge-arrow)"
            />
          )
        })}

        {nodes.map((n) => {
          const p = positions.get(n.id)
          if (!p) return null
          const row = n as {
            kind?: string
            sanctioned?: boolean
            scam?: boolean
            label?: string
            flags?: string[]
          }
          const isHub = (n.kind ?? '').toLowerCase().includes('wallet')
          const r = isHub ? 10 : 6
          return (
            <g key={n.id}>
              <circle
                cx={p.x}
                cy={p.y}
                r={r}
                fill={kindColor(n.kind, row)}
                stroke="rgba(218,227,238,0.35)"
                strokeWidth={1}
              />
              {isHub ? (
                <text
                  x={p.x}
                  y={p.y + r + 12}
                  textAnchor="middle"
                  fill="var(--fusion-text-secondary, #c2c6d6)"
                  fontSize={9}
                  fontFamily="ui-monospace, monospace"
                >
                  {shortEntityLabel(n.label ?? n.id, 22)}
                </text>
              ) : null}
            </g>
          )
        })}
      </svg>

      <ul className="fusion-report-doc__graph-legend">
        <li>
          <span className="dot" style={{ background: '#2ec4cf' }} /> wallet
        </li>
        <li>
          <span className="dot" style={{ background: '#ff4d4f' }} /> sanctioned
        </li>
        <li>
          <span className="dot" style={{ background: '#ff9f43' }} /> scam
        </li>
        <li>
          <span className="dot" style={{ background: '#d8baff' }} /> exchange/org
        </li>
        <li className="fusion-mono">
          {nodes.length} узлов · {edges.length} рёбер
        </li>
      </ul>

      {edges.length === 0 && nodes.length > 1 ? (
        <p className="fusion-text-micro text-[var(--fusion-ops-yellow)]">
          Узлы есть, рёбра отсутствуют в API — проверьте projection / Scalpel evidence_graph.
        </p>
      ) : null}

      {/* Hidden accessibility list so print still has edge inventory */}
      <details className="fusion-report-doc__edge-details">
        <summary className="fusion-text-micro">Список связей ({edges.length})</summary>
        <ul>
          {edges.slice(0, 40).map((e) => (
            <li key={e.id} className="fusion-mono fusion-text-micro">
              {shortEntityLabel(byId.get(e.source)?.label ?? e.source, 20)} —{e.rel_type ?? 'LINK'}→{' '}
              {shortEntityLabel(byId.get(e.target)?.label ?? e.target, 20)}
            </li>
          ))}
        </ul>
      </details>
    </div>
  )
}
