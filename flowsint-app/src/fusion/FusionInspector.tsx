import { useMemo } from 'react'
import type { EvidenceGraph } from '@/api/compliance-service'
import { cn } from '@/lib/utils'

type Props = {
  graph?: EvidenceGraph | null
  nodeId: string | null
  onClose: () => void
  onExpand?: (nodeId: string) => void
  className?: string
}

const KIND_GLYPH: Record<string, string> = {
  wallet: '⬡',
  address: '⬡',
  person: '◉',
  company: '▣',
  exchange: '◫',
  bank: '⛨',
  evidence: '▤',
  report: '▧',
  sanction: '⚠',
  transaction: '⇄',
  domain: '◎',
  default: '●',
}

function riskTone(risk?: number | null): string {
  if (risk == null) return 'var(--fusion-text-secondary)'
  if (risk >= 0.75) return 'var(--fusion-ops-red)'
  if (risk >= 0.5) return 'var(--fusion-ops-yellow)'
  return 'var(--fusion-ops-green)'
}

export function FusionInspector({ graph, nodeId, onClose, onExpand, className }: Props) {
  const node = useMemo(
    () => graph?.nodes?.find((n) => n.id === nodeId) ?? null,
    [graph, nodeId]
  )

  const edges = useMemo(() => {
    if (!nodeId || !graph?.edges) return []
    return graph.edges.filter((e) => e.source === nodeId || e.target === nodeId)
  }, [graph, nodeId])

  if (!nodeId || !node) return null

  const riskVal =
    typeof (node as { risk_score?: number }).risk_score === 'number'
      ? (node as unknown as { risk_score: number }).risk_score
      : null

  const glyph = KIND_GLYPH[node.kind?.toLowerCase() ?? ''] ?? KIND_GLYPH.default
  const confidence =
    typeof node.confidence === 'number' ? `${Math.round(node.confidence * 100)}%` : '—'

  return (
    <aside
      className={cn('fusion-inspector', className)}
      role="complementary"
      aria-label="Инспектор сущности"
    >
      <header className="fusion-inspector__header">
        <span className="fusion-inspector__glyph" aria-hidden>
          {glyph}
        </span>
        <div className="min-w-0 flex-1">
          <p className="fusion-text-micro text-[var(--fusion-text-tertiary)] uppercase">
            {node.kind ?? 'entity'}
          </p>
          <h3 className="fusion-heading-panel truncate normal-case tracking-normal">
            {node.label}
          </h3>
        </div>
        <button
          type="button"
          className="fusion-panel__btn"
          onClick={onClose}
          aria-label="Закрыть инспектор"
        >
          ×
        </button>
      </header>

      <div className="fusion-inspector__body custom-scrollbar">
        <section className="fusion-inspector__section">
          <h4 className="fusion-text-micro text-[var(--fusion-text-tertiary)]">РИСК</h4>
          <p className="fusion-mono fusion-text-data" style={{ color: riskTone(riskVal) }}>
            {riskVal != null ? `${Math.round(riskVal * 100)}/100` : '—'}
          </p>
        </section>

        <section className="fusion-inspector__section">
          <h4 className="fusion-text-micro text-[var(--fusion-text-tertiary)]">УВЕРЕННОСТЬ</h4>
          <p className="fusion-mono fusion-text-data">{confidence}</p>
        </section>

        <section className="fusion-inspector__section">
          <h4 className="fusion-text-micro text-[var(--fusion-text-tertiary)]">СВЯЗИ</h4>
          <ul className="space-y-1">
            {edges.length === 0 ? (
              <li className="fusion-text-micro text-[var(--fusion-text-tertiary)]">Нет рёбер</li>
            ) : (
              edges.slice(0, 12).map((e) => (
                <li key={e.id} className="fusion-text-data truncate">
                  <span className="fusion-mono text-[var(--fusion-ops-cyan)]">{e.rel_type}</span>
                  <span className="fusion-text-micro ml-1">
                    {e.source === nodeId ? '→' : '←'} {e.source === nodeId ? e.target : e.source}
                  </span>
                </li>
              ))
            )}
          </ul>
        </section>

        <section className="fusion-inspector__section">
          <h4 className="fusion-text-micro text-[var(--fusion-text-tertiary)]">ID</h4>
          <p className="fusion-mono fusion-text-micro break-all">{node.id}</p>
        </section>
      </div>

      <footer className="fusion-inspector__footer">
        <button
          type="button"
          className="fusion-inspector__action"
          onClick={() => onExpand?.(nodeId)}
        >
          Расширить окрестность
        </button>
      </footer>
    </aside>
  )
}
