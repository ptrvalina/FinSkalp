import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react'

import { subscribeFusionSync } from './fusion-sync-bus'

export type FusionAnnouncePriority = 'polite' | 'assertive'

type AnnouncerContext = {
  announce: (message: string, priority?: FusionAnnouncePriority) => void
}

const FusionAnnouncerContext = createContext<AnnouncerContext | null>(null)

const DOCK_TAB_LABELS: Record<string, string> = {
  timeline: 'Timeline',
  evidence: 'Evidence',
  blockchain: 'Blockchain',
  reports: 'Reports',
  tasks: 'Tasks',
  transactions: 'Transactions',
  osint: 'OSINT',
  wallets: 'Wallets',
}

function scheduleAnnounce(setter: (msg: string) => void, message: string) {
  setter('')
  requestAnimationFrame(() => setter(message))
}

export function useFusionAnnouncer(): AnnouncerContext {
  const ctx = useContext(FusionAnnouncerContext)
  if (!ctx) {
    return { announce: () => {} }
  }
  return ctx
}

export function FusionLiveAnnouncerProvider({ children }: { children: ReactNode }) {
  const [politeMsg, setPoliteMsg] = useState('')
  const [assertiveMsg, setAssertiveMsg] = useState('')
  const prevLivePaused = useRef<boolean | null>(null)
  const prevDockTab = useRef<string | null>(null)

  const announce = useCallback((message: string, priority: FusionAnnouncePriority = 'polite') => {
    if (!message.trim()) return
    if (priority === 'assertive') {
      scheduleAnnounce(setAssertiveMsg, message)
    } else {
      scheduleAnnounce(setPoliteMsg, message)
    }
  }, [])

  useEffect(() => {
    return subscribeFusionSync((sync) => {
      if (prevLivePaused.current !== null && prevLivePaused.current !== sync.livePaused) {
        announce(sync.livePaused ? 'Live updates paused' : 'Live updates resumed')
      }
      prevLivePaused.current = sync.livePaused

      if (
        sync.activeDockTab &&
        prevDockTab.current !== null &&
        prevDockTab.current !== sync.activeDockTab
      ) {
        const label = DOCK_TAB_LABELS[sync.activeDockTab] ?? sync.activeDockTab
        announce(`Dock tab: ${label}`)
      }
      if (sync.activeDockTab) {
        prevDockTab.current = sync.activeDockTab
      }
    })
  }, [announce])

  return (
    <FusionAnnouncerContext.Provider value={{ announce }}>
      {children}
      <div className="fusion-sr-only" aria-live="polite" aria-atomic="true">
        {politeMsg}
      </div>
      <div className="fusion-sr-only" aria-live="assertive" aria-atomic="true">
        {assertiveMsg}
      </div>
    </FusionAnnouncerContext.Provider>
  )
}
