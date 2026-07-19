import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { useNavigate } from '@tanstack/react-router'
import { cn } from '@/lib/utils'
import { FusionCommandPalette } from './FusionCommandPalette'
import { FusionGlobalSearch } from './FusionGlobalSearch'
import { FusionLayoutPresetsMenu } from './FusionLayoutPresetsMenu'
import { loadLastCaseRef } from './fusion-mission-data'
import {
  toggleLivePaused,
  requestCenterGraph,
  setActiveDockTab,
  cycleActiveDockTab,
  setGlobalSearchOpen,
  setGraphSearchOpen,
  setPanelFocus,
  toggleExecutiveMode,
  toggleMoneyFlow,
  toggleCollaboration,
  setExecutiveMode,
  getFusionSyncState,
} from './fusion-sync-bus'
import { FUSION_PANEL_PINS_KEY, FUSION_LAYOUT_COMMAND_KEY, FUSION_LAYOUT_INVESTIGATION_KEY } from './fusion-layout-storage'

const SHORTCUTS = [
  { keys: 'Ctrl+K', desc: 'Командная палитра' },
  { keys: 'Ctrl+Shift+F', desc: 'Глобальный поиск разведки' },
  { keys: 'Ctrl+F', desc: 'Поиск на графе' },
  { keys: 'Ctrl+G', desc: 'Центрировать граф' },
  { keys: 'Ctrl+L', desc: 'Лента live-событий' },
  { keys: 'Ctrl+R', desc: 'Сгенерировать отчёт' },
  { keys: 'Ctrl+E', desc: 'Создать доказательство' },
  { keys: 'Space', desc: 'Пауза live-обновлений' },
  { keys: 'Alt+1', desc: 'Mission / очередь' },
  { keys: 'Alt+2', desc: 'Хронология' },
  { keys: 'Alt+3', desc: 'Доказательства' },
  { keys: 'Alt+4', desc: 'Отчёты' },
  { keys: 'Alt+5', desc: 'Офицер разведки' },
  { keys: 'Alt+6', desc: 'Слои графа' },
  { keys: 'G F', desc: 'Mission Control' },
  { keys: 'G I', desc: 'Последнее расследование' },
  { keys: 'G C', desc: 'Поиск дела' },
  { keys: '/', desc: 'Фокус фильтра очереди' },
  { keys: 'Tab', desc: 'Следующая панель (в dock)' },
  { keys: 'Esc', desc: 'Закрыть оверлеи' },
  { keys: '?', desc: 'Справка по клавишам' },
  { keys: 'Shift+Alt+R', desc: 'Сброс раскладки' },
  { keys: 'Shift+Alt+L', desc: 'Рабочие раскладки' },
  { keys: 'Shift+Alt+E', desc: 'Executive briefing mode' },
  { keys: 'Shift+Alt+M', desc: 'Money flow particles' },
  { keys: 'Shift+Alt+U', desc: 'Live analyst cursors' },
]
type FilterRegistrar = (el: HTMLInputElement | null) => void

type FusionKeyboardContextValue = {
  registerFilterInput: FilterRegistrar
  focusFilter: () => void
  registerFloatCloser: (fn: () => void) => () => void
  openCaseSearch: () => void
  closeCaseSearch: () => void
  caseSearchOpen: boolean
}

const FusionKeyboardContext = createContext<FusionKeyboardContextValue | null>(null)

export function useFusionKeyboard() {
  return useContext(FusionKeyboardContext)
}

type KeyboardProviderProps = {
  children: ReactNode
  caseRef?: string | null
  onGenerateReport?: () => void
  onCreateEvidence?: () => void
}

function isTypingTarget(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false
  const tag = el.tagName
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || el.isContentEditable
}

export function FusionKeyboardProvider({
  children,
  caseRef,
  onGenerateReport,
  onCreateEvidence,
}: KeyboardProviderProps) {
  const navigate = useNavigate()
  const [helpOpen, setHelpOpen] = useState(false)
  const [caseSearchOpen, setCaseSearchOpen] = useState(false)
  const [commandOpen, setCommandOpen] = useState(false)
  const [layoutsOpen, setLayoutsOpen] = useState(false)
  const [globalSearchOpen, setGlobalSearchOpenState] = useState(false)
  const [chord, setChord] = useState<'g' | null>(null)
  const filterRef = useRef<HTMLInputElement | null>(null)
  const floatClosersRef = useRef<Set<() => void>>(new Set())
  const chordTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const registerFilterInput = useCallback<FilterRegistrar>((el) => {
    filterRef.current = el
  }, [])

  const focusFilter = useCallback(() => {
    filterRef.current?.focus()
    filterRef.current?.select()
  }, [])

  const registerFloatCloser = useCallback((fn: () => void) => {
    floatClosersRef.current.add(fn)
    return () => floatClosersRef.current.delete(fn)
  }, [])

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

  const closeAllOverlays = useCallback(() => {
    if (commandOpen) {
      setCommandOpen(false)
      return true
    }
    if (globalSearchOpen) {
      setGlobalSearchOpenState(false)
      return true
    }
    if (helpOpen) {
      setHelpOpen(false)
      return true
    }
    if (caseSearchOpen) {
      setCaseSearchOpen(false)
      return true
    }
    if (layoutsOpen) {
      setLayoutsOpen(false)
      return true
    }
    for (const closer of floatClosersRef.current) {
      closer()
      return true
    }
    return false
  }, [commandOpen, globalSearchOpen, helpOpen, caseSearchOpen, layoutsOpen])

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setCommandOpen((v) => !v)
        return
      }

      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'f') {
        e.preventDefault()
        setGlobalSearchOpen(true)
        setGlobalSearchOpenState(true)
        return
      }

      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'f' && !e.shiftKey) {
        e.preventDefault()
        setGraphSearchOpen(true)
        return
      }

      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'g') {
        e.preventDefault()
        requestCenterGraph()
        return
      }

      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'l') {
        e.preventDefault()
        setPanelFocus('live-feed')
        setActiveDockTab('transactions')
        return
      }

      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'r') {
        e.preventDefault()
        onGenerateReport?.()
        return
      }

      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'e') {
        e.preventDefault()
        onCreateEvidence?.()
        return
      }

      if (e.altKey && !e.ctrlKey && !e.metaKey) {
        const dockByAlt: Record<string, 'evidence' | 'reports' | 'transactions' | 'blockchain' | 'osint'> = {
          '3': 'evidence',
          '4': 'reports',
        }
        const focusByAlt: Record<string, 'mission' | 'timeline' | 'mio' | 'graph-layers' | 'live-feed'> = {
          '1': 'mission',
          '2': 'timeline',
          '5': 'mio',
          '6': 'graph-layers',
        }
        if (dockByAlt[e.key]) {
          e.preventDefault()
          setActiveDockTab(dockByAlt[e.key])
          return
        }
        if (focusByAlt[e.key]) {
          e.preventDefault()
          setPanelFocus(focusByAlt[e.key])
          return
        }
      }

      if (e.key === 'Tab' && !e.ctrlKey && !e.metaKey && !e.altKey && !isTypingTarget(e.target)) {
        e.preventDefault()
        cycleActiveDockTab()
        return
      }

      if (e.key === ' ' && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault()
        toggleLivePaused()
        return
      }

      if (e.shiftKey && e.altKey && e.key.toLowerCase() === 'r') {
        e.preventDefault()
        resetLayout()
        return
      }

      if (e.shiftKey && e.altKey && e.key.toLowerCase() === 'l') {
        e.preventDefault()
        setLayoutsOpen(true)
        return
      }

      if (e.shiftKey && e.altKey && e.key.toLowerCase() === 'e') {
        e.preventDefault()
        toggleExecutiveMode()
        return
      }

      if (e.shiftKey && e.altKey && e.key.toLowerCase() === 'm') {
        e.preventDefault()
        toggleMoneyFlow()
        return
      }

      if (e.shiftKey && e.altKey && e.key.toLowerCase() === 'u') {
        e.preventDefault()
        toggleCollaboration()
        return
      }

      if (e.key === 'Escape') {
        if (getFusionSyncState().executiveMode) {
          e.preventDefault()
          setExecutiveMode(false)
          return
        }
        if (closeAllOverlays()) {
          e.preventDefault()
        }
        setChord(null)
        return
      }

      if (isTypingTarget(e.target)) return

      if (e.key === '?' && !e.ctrlKey && !e.metaKey) {
        e.preventDefault()
        setHelpOpen((v) => !v)
        return
      }

      if (e.key === '/') {
        e.preventDefault()
        focusFilter()
        return
      }

      if (chord === 'g') {
        e.preventDefault()
        setChord(null)
        if (chordTimerRef.current) clearTimeout(chordTimerRef.current)
        const key = e.key.toLowerCase()
        if (key === 'f') {
          navigate({ to: '/dashboard/fusion' })
        } else if (key === 'i') {
          const last = loadLastCaseRef()
          if (last) {
            navigate({
              to: '/dashboard/fusion/investigation/$caseRef',
              params: { caseRef: last },
            })
          }
        } else if (key === 'c') {
          setCaseSearchOpen(true)
        }
        return
      }

      if (e.key.toLowerCase() === 'g' && !e.ctrlKey && !e.metaKey) {
        e.preventDefault()
        setChord('g')
        if (chordTimerRef.current) clearTimeout(chordTimerRef.current)
        chordTimerRef.current = setTimeout(() => setChord(null), 1200)
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [chord, closeAllOverlays, focusFilter, navigate, resetLayout, onGenerateReport, onCreateEvidence])

  return (
    <FusionKeyboardContext.Provider
      value={{
        registerFilterInput,
        focusFilter,
        registerFloatCloser,
        openCaseSearch: () => setCaseSearchOpen(true),
        closeCaseSearch: () => setCaseSearchOpen(false),
        caseSearchOpen,
      }}
    >
      {children}
      {helpOpen ? (
        <div
          className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 p-4"
          role="dialog"
          aria-label="Keyboard shortcuts"
          onClick={() => setHelpOpen(false)}
        >
          <div
            className="fusion-surface-panel max-h-[80vh] w-full max-w-md overflow-auto p-4"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="fusion-heading-panel mb-3">Горячие клавиши</h2>
            <ul className="space-y-2">
              {SHORTCUTS.map((s) => (
                <li key={s.keys} className="flex items-center justify-between gap-4">
                  <kbd className="fusion-mono fusion-text-micro rounded border border-[var(--fusion-border)] px-2 py-0.5">
                    {s.keys}
                  </kbd>
                  <span className="fusion-text-data text-right">{s.desc}</span>
                </li>
              ))}
            </ul>
            <p className="fusion-text-micro mt-4 text-[var(--fusion-text-tertiary)]">
              Press <kbd className="fusion-mono">?</kbd> or Esc to close
            </p>
          </div>
        </div>
      ) : null}
      {caseSearchOpen ? (
        <FusionCaseSearchOverlay onClose={() => setCaseSearchOpen(false)} />
      ) : null}
      <FusionCommandPalette
        open={commandOpen}
        onOpenChange={setCommandOpen}
        caseRef={caseRef}
        onFocusFilter={focusFilter}
        onGenerateReport={onGenerateReport}
        onOpenCaseSearch={() => {
          setCommandOpen(false)
          setCaseSearchOpen(true)
        }}
        onOpenKeyboardHelp={() => {
          setCommandOpen(false)
          setHelpOpen(true)
        }}
        onOpenLayouts={() => {
          setCommandOpen(false)
          setLayoutsOpen(true)
        }}
      />
      <FusionLayoutPresetsMenu open={layoutsOpen} onClose={() => setLayoutsOpen(false)} />
      <FusionGlobalSearch open={globalSearchOpen} onClose={() => setGlobalSearchOpenState(false)} />
    </FusionKeyboardContext.Provider>
  )
}

function FusionCaseSearchOverlay({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<
    Array<{ case_ref?: string; display_name?: string; kind: string }>
  >([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  useEffect(() => {
    if (!query.trim()) {
      setResults([])
      return
    }
    const t = setTimeout(async () => {
      setLoading(true)
      try {
        const { complianceService } = await import('@/api/compliance-service')
        const res = await complianceService.searchAnalystWorkspace({ query: query.trim() })
        setResults(
          res.results
            .filter((r) => r.kind === 'case' && r.case_ref)
            .slice(0, 8)
            .map((r) => ({
              case_ref: r.case_ref,
              display_name: r.display_name,
              kind: r.kind,
            }))
        )
      } catch {
        setResults([])
      } finally {
        setLoading(false)
      }
    }, 250)
    return () => clearTimeout(t)
  }, [query])

  return (
    <div
      className="fixed inset-0 z-[200] flex items-start justify-center bg-black/60 p-4 pt-[12vh]"
      role="dialog"
      aria-label="Case search"
      onClick={onClose}
    >
      <div
        className="fusion-surface-panel w-full max-w-lg p-3"
        onClick={(e) => e.stopPropagation()}
      >
        <input
          ref={inputRef}
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search cases…"
          className="w-full bg-transparent fusion-text-data outline-none border-b border-[var(--fusion-border)] pb-2"
          onKeyDown={(e) => {
            if (e.key === 'Escape') onClose()
          }}
        />
        <ul className="mt-2 max-h-64 overflow-auto">
          {loading ? (
            <li className="fusion-text-micro py-3 text-center">Searching…</li>
          ) : results.length === 0 ? (
            <li className="fusion-text-micro py-3 text-center text-[var(--fusion-text-tertiary)]">
              {query.trim() ? 'No cases found' : 'Type to search cases'}
            </li>
          ) : (
            results.map((r) => (
              <li key={r.case_ref}>
                <button
                  type="button"
                  className={cn(
                    'w-full px-2 py-2 text-left hover:bg-[var(--fusion-bg-raised)] fusion-text-data'
                  )}
                  onClick={() => {
                    if (r.case_ref) {
                      navigate({
                        to: '/dashboard/fusion/investigation/$caseRef',
                        params: { caseRef: r.case_ref },
                      })
                      onClose()
                    }
                  }}
                >
                  <span className="fusion-mono text-[var(--fusion-ops-blue)]">{r.case_ref}</span>
                  {r.display_name ? (
                    <span className="ml-2 fusion-text-micro">{r.display_name}</span>
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
