import { useEffect, useRef, useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { cn } from '@/lib/utils'
import { complianceService } from '@/api/compliance-service'

type SearchResult = {
  kind: string
  case_ref?: string
  display_name?: string
  entity_key?: string
}

type Props = {
  open: boolean
  onClose: () => void
}

const KIND_RU: Record<string, string> = {
  case: 'Дело',
  wallet: 'Кошелёк',
  entity: 'Сущность',
  report: 'Отчёт',
  transaction: 'Транзакция',
  company: 'Компания',
  person: 'Персона',
}

export function FusionGlobalSearch({ open, onClose }: Props) {
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [activeIdx, setActiveIdx] = useState(0)

  useEffect(() => {
    if (open) {
      inputRef.current?.focus()
      setQuery('')
      setResults([])
      setActiveIdx(0)
    }
  }, [open])

  useEffect(() => {
    if (!open || !query.trim()) {
      setResults([])
      return
    }
    const t = setTimeout(async () => {
      setLoading(true)
      try {
        const res = await complianceService.searchAnalystWorkspace({ query: query.trim() })
        setResults(res.results.slice(0, 16) as SearchResult[])
        setActiveIdx(0)
      } catch {
        setResults([])
      } finally {
        setLoading(false)
      }
    }, 200)
    return () => clearTimeout(t)
  }, [open, query])

  const openResult = (r: SearchResult) => {
    onClose()
    if (r.kind === 'case' && r.case_ref) {
      navigate({
        to: '/dashboard/fusion/investigation/$caseRef',
        params: { caseRef: r.case_ref },
      })
      return
    }
    if (r.case_ref) {
      navigate({
        to: '/dashboard/fusion/investigation/$caseRef',
        params: { caseRef: r.case_ref },
      })
    }
  }

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-[220] flex items-start justify-center bg-black/70 p-4 pt-[8vh]"
      role="dialog"
      aria-label="Глобальный поиск разведки"
      onClick={onClose}
    >
      <div
        className="fusion-surface-panel w-full max-w-2xl overflow-hidden shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="border-b border-[var(--fusion-border)] px-4 py-3">
          <p className="fusion-text-micro mb-2 text-[var(--fusion-ops-purple)]">
            ГЛОБАЛЬНЫЙ ПОИСК РАЗВЕДКИ · Ctrl+Shift+F
          </p>
          <input
            ref={inputRef}
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Кошелёк, дело, транзакция, компания…"
            className="w-full bg-transparent text-lg outline-none fusion-text-data"
            onKeyDown={(e) => {
              if (e.key === 'Escape') onClose()
              if (e.key === 'ArrowDown') {
                e.preventDefault()
                setActiveIdx((i) => Math.min(i + 1, results.length - 1))
              }
              if (e.key === 'ArrowUp') {
                e.preventDefault()
                setActiveIdx((i) => Math.max(i - 1, 0))
              }
              if (e.key === 'Enter' && results[activeIdx]) openResult(results[activeIdx])
            }}
          />
        </div>
        <ul className="max-h-[50vh] overflow-auto py-1">
          {loading ? (
            <li className="fusion-text-micro py-6 text-center">Поиск…</li>
          ) : results.length === 0 ? (
            <li className="fusion-text-micro py-6 text-center text-[var(--fusion-text-tertiary)]">
              {query.trim() ? 'Ничего не найдено' : 'Введите запрос — камера перейдёт к объекту'}
            </li>
          ) : (
            results.map((r, i) => (
              <li key={`${r.kind}-${r.case_ref}-${r.entity_key}-${i}`}>
                <button
                  type="button"
                  className={cn(
                    'flex w-full items-center gap-3 px-4 py-2.5 text-left',
                    i === activeIdx
                      ? 'bg-[var(--fusion-bg-interactive)]'
                      : 'hover:bg-[var(--fusion-bg-raised)]'
                  )}
                  onClick={() => openResult(r)}
                >
                  <span className="fusion-text-micro w-20 shrink-0 text-[var(--fusion-ops-purple)]">
                    {KIND_RU[r.kind] ?? r.kind}
                  </span>
                  <span className="fusion-mono fusion-text-data truncate">
                    {r.case_ref ?? r.display_name ?? r.entity_key ?? '—'}
                  </span>
                  {r.display_name && r.case_ref ? (
                    <span className="fusion-text-micro ml-auto truncate text-[var(--fusion-text-tertiary)]">
                      {r.display_name}
                    </span>
                  ) : null}
                </button>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  )
}
