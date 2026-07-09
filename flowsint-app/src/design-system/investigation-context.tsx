/** RFC-0008 Ch.1 — Context Preservation for Investigation First */

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

export type InvestigationUiContext = {
  investigationId: string | null
  caseRef: string | null
  selectedEntityId: string | null
  filters: Record<string, unknown>
  dateRange: { from?: string; to?: string } | null
  graphZoom: number
}

const STORAGE_KEY = 'finskalp.investigation.ui.context'

const defaultState: InvestigationUiContext = {
  investigationId: null,
  caseRef: null,
  selectedEntityId: null,
  filters: {},
  dateRange: null,
  graphZoom: 1,
}

type Ctx = {
  context: InvestigationUiContext
  setInvestigationId: (id: string | null) => void
  setCaseRef: (ref: string | null) => void
  setSelectedEntityId: (id: string | null) => void
  setFilters: (filters: Record<string, unknown>) => void
  setDateRange: (range: InvestigationUiContext['dateRange']) => void
  setGraphZoom: (zoom: number) => void
  reset: () => void
}

const InvestigationContext = createContext<Ctx | null>(null)

function loadStored(): InvestigationUiContext {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return defaultState
    return { ...defaultState, ...JSON.parse(raw) }
  } catch {
    return defaultState
  }
}

function persist(state: InvestigationUiContext) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {
    /* ignore */
  }
}

export function InvestigationContextProvider({ children }: { children: ReactNode }) {
  const [context, setContext] = useState<InvestigationUiContext>(loadStored)

  const patch = useCallback((partial: Partial<InvestigationUiContext>) => {
    setContext((prev) => {
      const next = { ...prev, ...partial }
      persist(next)
      return next
    })
  }, [])

  const value = useMemo<Ctx>(
    () => ({
      context,
      setInvestigationId: (id) => patch({ investigationId: id }),
      setCaseRef: (ref) => patch({ caseRef: ref }),
      setSelectedEntityId: (id) => patch({ selectedEntityId: id }),
      setFilters: (filters) => patch({ filters }),
      setDateRange: (dateRange) => patch({ dateRange }),
      setGraphZoom: (graphZoom) => patch({ graphZoom }),
      reset: () => {
        setContext(defaultState)
        sessionStorage.removeItem(STORAGE_KEY)
      },
    }),
    [context, patch]
  )

  return <InvestigationContext.Provider value={value}>{children}</InvestigationContext.Provider>
}

export function useInvestigationUiContext() {
  const ctx = useContext(InvestigationContext)
  if (!ctx) {
    throw new Error('useInvestigationUiContext requires InvestigationContextProvider')
  }
  return ctx
}
