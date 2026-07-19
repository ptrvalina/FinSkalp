import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { cn } from '@/lib/utils'
import { loadLastCaseRef } from './fusion-mission-data'
import { FusionInlineError } from './FusionInlineError'
import {
  FUSION_LAYOUT_COMMAND_KEY,
  FUSION_LAYOUT_INVESTIGATION_KEY,
  FUSION_PANEL_PINS_KEY,
} from './fusion-layout-storage'
import {
  requestCenterGraph,
  setActiveDockTab,
  setGraphSearchOpen,
  toggleLivePaused,
} from './fusion-sync-bus'

export type FusionCommandDef = {
  id: string
  label_ru: string
  shortcut?: string
  group?: string
}

const CONSTITUTION_COMMANDS: FusionCommandDef[] = [
  { id: 'find_case', label_ru: 'Найти дело', shortcut: 'G C', group: 'Навигация' },
  { id: 'global_search', label_ru: 'Глобальный поиск разведки', shortcut: 'Ctrl+Shift+F', group: 'Навигация' },
  { id: 'graph_search', label_ru: 'Поиск на графе', shortcut: 'Ctrl+F', group: 'Граф' },
  { id: 'center_graph', label_ru: 'Центрировать граф', shortcut: 'Ctrl+G', group: 'Граф' },
  { id: 'open_timeline', label_ru: 'Открыть хронологию', shortcut: 'Alt+2', group: 'Расследование' },
  { id: 'open_evidence', label_ru: 'Доказательства', shortcut: 'Alt+3', group: 'Расследование' },
  { id: 'generate_report', label_ru: 'Сгенерировать отчёт', shortcut: 'Ctrl+R', group: 'Расследование' },
  { id: 'mission_control', label_ru: 'Mission Control', shortcut: 'G F', group: 'Навигация' },
  { id: 'last_investigation', label_ru: 'Последнее расследование', shortcut: 'G I', group: 'Навигация' },
  { id: 'toggle_live', label_ru: 'Пауза live-обновлений', shortcut: 'Space', group: 'Система' },
  { id: 'focus_filter', label_ru: 'Фокус фильтра очереди', shortcut: '/', group: 'Очередь' },
  { id: 'keyboard_help', label_ru: 'Справка по клавишам', shortcut: '?', group: 'Система' },
  { id: 'reset_layout', label_ru: 'Сбросить раскладку', shortcut: 'Shift+Alt+R', group: 'Система' },
  { id: 'layout_presets', label_ru: 'Рабочие раскладки', shortcut: 'Shift+Alt+L', group: 'Система' },
]

type Props = {
  open: boolean
  onOpenChange: (open: boolean) => void
  caseRef?: string | null
  onFocusFilter?: () => void
  onOpenCaseSearch?: () => void
  onOpenKeyboardHelp?: () => void
  onOpenLayouts?: () => void
  onGenerateReport?: () => void
}

export function FusionCommandPalette({
  open,
  onOpenChange,
  caseRef,
  onFocusFilter,
  onOpenCaseSearch,
  onOpenKeyboardHelp,
  onOpenLayouts,
  onGenerateReport,
}: Props) {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [entityResults, setEntityResults] = useState<
    Array<{ case_ref?: string; display_name?: string; kind: string }>
  >([])
  const [loading, setLoading] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) {
      setQuery('')
      setEntityResults([])
      setSearchError(null)
    }
  }, [open])

  useEffect(() => {
    if (!open || !query.trim()) {
      setEntityResults([])
      setSearchError(null)
      return
    }
    const t = setTimeout(async () => {
      setLoading(true)
      setSearchError(null)
      try {
        const { complianceService } = await import('@/api/compliance-service')
        const res = await complianceService.searchAnalystWorkspace({ query: query.trim() })
        setEntityResults(res.results.slice(0, 8))
      } catch (err) {
        setEntityResults([])
        setSearchError(err instanceof Error ? err.message : 'Entity search failed')
      } finally {
        setLoading(false)
      }
    }, 250)
    return () => clearTimeout(t)
  }, [open, query])

  const filteredCommands = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return CONSTITUTION_COMMANDS
    return CONSTITUTION_COMMANDS.filter(
      (cmd) =>
        cmd.label_ru.toLowerCase().includes(q) ||
        cmd.id.toLowerCase().includes(q) ||
        (cmd.group ?? '').toLowerCase().includes(q)
    )
  }, [query])

  const resetLayout = useCallback(() => {
    try {
      localStorage.removeItem(FUSION_LAYOUT_COMMAND_KEY)
      localStorage.removeItem(FUSION_LAYOUT_INVESTIGATION_KEY)
      localStorage.removeItem(FUSION_PANEL_PINS_KEY)
      window.location.reload()
    } catch {
      /* ignore */
    }
  }, [])

  const runCommand = useCallback(
    (id: string) => {
      onOpenChange(false)
      switch (id) {
        case 'find_case':
          onOpenCaseSearch?.()
          break
        case 'global_search':
          break
        case 'graph_search':
          setGraphSearchOpen(true)
          break
        case 'center_graph':
          requestCenterGraph()
          break
        case 'open_evidence':
          setActiveDockTab('evidence')
          break
        case 'generate_report':
          onGenerateReport?.()
          break
        case 'toggle_live':
          toggleLivePaused()
          break
        case 'focus_entity':
          break
        case 'open_timeline': {
          const ref = caseRef ?? loadLastCaseRef()
          if (ref) {
            navigate({
              to: '/dashboard/fusion/investigation/$caseRef',
              params: { caseRef: ref },
            })
          }
          break
        }
        case 'mission_control':
          navigate({ to: '/dashboard/fusion' })
          break
        case 'last_investigation': {
          const last = loadLastCaseRef()
          if (last) {
            navigate({
              to: '/dashboard/fusion/investigation/$caseRef',
              params: { caseRef: last },
            })
          }
          break
        }
        case 'focus_filter':
          onFocusFilter?.()
          break
        case 'keyboard_help':
          onOpenKeyboardHelp?.()
          break
        case 'reset_layout':
          resetLayout()
          break
        case 'layout_presets':
          onOpenLayouts?.()
          break
        default:
          break
      }
    },
    [
      caseRef,
      navigate,
      onFocusFilter,
      onOpenCaseSearch,
      onOpenChange,
      onOpenKeyboardHelp,
      onOpenLayouts,
      resetLayout,
    ]
  )

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-[210] flex items-start justify-center bg-black/60 p-4 pt-[10vh]"
      role="dialog"
      aria-label="Command palette"
      onClick={() => onOpenChange(false)}
    >
      <div
        className="fusion-surface-panel w-full max-w-lg overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="border-b border-[var(--fusion-border)] px-3 py-2">
          <input
            autoFocus
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Команда или сущность…"
            className="w-full bg-transparent fusion-text-data outline-none"
            onKeyDown={(e) => {
              if (e.key === 'Escape') onOpenChange(false)
              if (e.key === 'Enter' && filteredCommands[0]) runCommand(filteredCommands[0].id)
            }}
          />
          <p className="fusion-text-micro mt-1 text-[var(--fusion-text-tertiary)]">
            Ctrl+K · FinSkalp
          </p>
          {searchError && query.trim() ? (
            <FusionInlineError message={searchError} className="mt-2" />
          ) : null}
        </div>
        <div className="max-h-80 overflow-auto">
          {query.trim() && entityResults.length > 0 ? (
            <section className="py-1">
              <p className="fusion-text-micro px-3 py-1 text-[var(--fusion-text-tertiary)]">
                СУЩНОСТИ
              </p>
              {entityResults.map((r, i) => (
                <button
                  key={`${r.kind}-${r.case_ref ?? r.display_name}-${i}`}
                  type="button"
                  className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-[var(--fusion-bg-interactive)] fusion-text-data"
                  onClick={() => {
                    onOpenChange(false)
                    if (r.kind === 'case' && r.case_ref) {
                      navigate({
                        to: '/dashboard/fusion/investigation/$caseRef',
                        params: { caseRef: r.case_ref },
                      })
                    }
                  }}
                >
                  <span className="fusion-text-micro fusion-tone-ops">{r.kind}</span>
                  <span className="fusion-mono">{r.case_ref ?? r.display_name ?? '—'}</span>
                </button>
              ))}
            </section>
          ) : null}
          {loading ? (
            <p className="fusion-text-micro py-4 text-center">Поиск…</p>
          ) : (
            <section className="py-1">
              <p className="fusion-text-micro px-3 py-1 text-[var(--fusion-text-tertiary)]">
                КОМАНДЫ
              </p>
              {filteredCommands.length === 0 ? (
                <p className="fusion-text-micro py-4 text-center text-[var(--fusion-text-tertiary)]">
                  Нет команд
                </p>
              ) : (
                filteredCommands.map((cmd) => (
                  <button
                    key={cmd.id}
                    type="button"
                    className={cn(
                      'flex w-full items-center justify-between gap-3 px-3 py-2 text-left',
                      'hover:bg-[var(--fusion-bg-interactive)] fusion-text-data'
                    )}
                    onClick={() => runCommand(cmd.id)}
                  >
                    <span>{cmd.label_ru}</span>
                    {cmd.shortcut ? (
                      <kbd className="fusion-mono fusion-text-micro rounded border border-[var(--fusion-border)] px-1.5 py-0.5 text-[var(--fusion-text-tertiary)]">
                        {cmd.shortcut}
                      </kbd>
                    ) : null}
                  </button>
                ))
              )}
            </section>
          )}
        </div>
      </div>
    </div>
  )
}
