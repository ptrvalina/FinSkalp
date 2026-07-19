import { useEffect, useMemo, useRef, useState } from 'react'
import type { EvidenceGraph } from '@/api/compliance-service'
import { requestGraphNodeFocus, setGraphSearchOpen } from './fusion-sync-bus'
import { useFusionAnnouncer } from './useFusionAnnouncer'

type Props = {
  open: boolean
  graph?: EvidenceGraph | null
  onSelectNode?: (nodeId: string) => void
}

export function FusionGraphSearchPanel({ open, graph, onSelectNode }: Props) {
  const { announce } = useFusionAnnouncer()
  const inputRef = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState('')
  const lastAnnouncedQuery = useRef('')

  useEffect(() => {
    if (open) {
      setQuery('')
      lastAnnouncedQuery.current = ''
      setTimeout(() => inputRef.current?.focus(), 0)
    }
  }, [open])

  const matches = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q || !graph?.nodes?.length) return []
    return graph.nodes
      .filter(
        (n) =>
          n.id.toLowerCase().includes(q) ||
          n.label.toLowerCase().includes(q) ||
          (n.kind ?? '').toLowerCase().includes(q)
      )
      .slice(0, 12)
  }, [graph, query])

  useEffect(() => {
    if (!open) return
    const q = query.trim()
    if (!q || q === lastAnnouncedQuery.current) return
    lastAnnouncedQuery.current = q
    if (matches.length === 0) {
      announce('Graph search: no matches')
    } else {
      announce(`Graph search: ${matches.length} match${matches.length === 1 ? '' : 'es'}`)
    }
  }, [announce, matches.length, open, query])

  if (!open) return null

  const pick = (nodeId: string) => {
    const node = graph?.nodes?.find((n) => n.id === nodeId)
    requestGraphNodeFocus(nodeId)
    onSelectNode?.(nodeId)
    announce(`Graph focus: ${node?.label ?? nodeId}`)
    setGraphSearchOpen(false)
  }

  return (
    <div
      className="fusion-graph-search"
      role="dialog"
      aria-label="Graph search"
      onKeyDown={(e) => {
        if (e.key === 'Escape') setGraphSearchOpen(false)
      }}
    >
      <input
        ref={inputRef}
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="ID, label, kind…"
        className="fusion-graph-search__input"
        aria-label="Search graph nodes by ID, label, or kind"
        onKeyDown={(e) => {
          if (e.key === 'Enter' && matches[0]) pick(matches[0].id)
        }}
      />
      <ul
        className="fusion-graph-search__results custom-scrollbar"
        aria-label={`${matches.length} search results`}
      >
        {matches.length === 0 ? (
          <li className="fusion-text-micro px-2 py-2 text-[var(--fusion-text-tertiary)]">
            {query.trim() ? 'Нет совпадений' : 'Введите запрос'}
          </li>
        ) : (
          matches.map((n) => (
            <li key={n.id}>
              <button
                type="button"
                className="fusion-graph-search__row"
                onClick={() => pick(n.id)}
                aria-label={`Focus node ${n.label}, kind ${n.kind}`}
              >
                <span className="fusion-mono text-[var(--fusion-ops-blue)] truncate">{n.label}</span>
                <span className="fusion-text-micro shrink-0">{n.kind}</span>
              </button>
            </li>
          ))
        )}
      </ul>
      <button
        type="button"
        className="fusion-graph-search__close fusion-text-micro"
        onClick={() => setGraphSearchOpen(false)}
        aria-label="Close graph search"
      >
        Esc — закрыть
      </button>
    </div>
  )
}
