import { useEffect, useState } from 'react'

import type { MIOActionCard } from './FusionMIO'
import type { MioActionKind, MioExecutableCard } from './fusion-mio-actions'

/** Default auto-refresh interval for MIO recommendations (ms). */
export const MIO_AUTO_REFRESH_MS = 45_000

const ACTION_KIND_ORDER: Record<MioActionKind, number> = {
  fuse: 0,
  run_scalpel: 0,
  transition: 1,
  screen_wallet: 2,
  open_report: 3,
  open_evidence: 4,
  refresh_graph: 4,
  focus_seed: 4,
}

const PRIORITY_ORDER: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
}

export type BatchProgress = {
  current: number
  total: number
  cardId: string
  label?: string
}

export type BatchResult = {
  succeeded: string[]
  failed: Array<{ cardId: string; error: string }>
}

export function pickBriefingCards(cards: MIOActionCard[], limit = 3): MIOActionCard[] {
  return [...cards]
    .sort(
      (a, b) =>
        (PRIORITY_ORDER[a.priority ?? 'medium'] ?? 2) -
        (PRIORITY_ORDER[b.priority ?? 'medium'] ?? 2)
    )
    .slice(0, limit)
}

/** Order cards so workflow mutations run before read-only actions. */
export function sortBatchExecutionOrder(cards: MioExecutableCard[]): MioExecutableCard[] {
  return [...cards].sort((a, b) => {
    const kindA = ACTION_KIND_ORDER[a.actionKind ?? 'transition'] ?? 1
    const kindB = ACTION_KIND_ORDER[b.actionKind ?? 'transition'] ?? 1
    if (kindA !== kindB) return kindA - kindB
    return (
      (PRIORITY_ORDER[a.priority ?? 'medium'] ?? 2) -
      (PRIORITY_ORDER[b.priority ?? 'medium'] ?? 2)
    )
  })
}

export function getBatchDependencyHint(cards: MioExecutableCard[]): string | null {
  const kinds = new Set(cards.map((c) => c.actionKind).filter(Boolean))
  if (kinds.has('fuse') && kinds.has('transition')) {
    return 'Fusion → workflow transition'
  }
  if (cards.filter((c) => c.actionKind === 'transition').length > 1) {
    return 'Multiple transitions — sequential order'
  }
  if (kinds.has('screen_wallet') && kinds.has('fuse')) {
    return 'Fusion before wallet screening'
  }
  return null
}

export async function runMioBatch(
  cards: MioExecutableCard[],
  executeOne: (card: MioExecutableCard) => Promise<void>,
  onProgress?: (progress: BatchProgress) => void,
  options?: { shouldCancel?: () => boolean }
): Promise<BatchResult> {
  const ordered = sortBatchExecutionOrder(cards)
  const succeeded: string[] = []
  const failed: Array<{ cardId: string; error: string }> = []

  for (let i = 0; i < ordered.length; i++) {
    if (options?.shouldCancel?.()) {
      failed.push({ cardId: '__cancelled__', error: 'cancelled' })
      break
    }
    const card = ordered[i]!
    onProgress?.({
      current: i + 1,
      total: ordered.length,
      cardId: card.id,
      label: card.title,
    })
    try {
      await executeOne(card)
      succeeded.push(card.id)
    } catch (err) {
      failed.push({
        cardId: card.id,
        error: err instanceof Error ? err.message : 'Execution failed',
      })
    }
  }

  return { succeeded, failed }
}

/**
 * React-query refetchInterval helper — pauses when live is paused or tab hidden.
 */
export function useFusionLiveRefetchInterval(
  livePaused: boolean,
  enabled = true,
  intervalMs = MIO_AUTO_REFRESH_MS
): number | false {
  const [visible, setVisible] = useState(() =>
    typeof document !== 'undefined' ? document.visibilityState === 'visible' : true
  )

  useEffect(() => {
    const handler = () => setVisible(document.visibilityState === 'visible')
    document.addEventListener('visibilitychange', handler)
    return () => document.removeEventListener('visibilitychange', handler)
  }, [])

  if (!enabled || livePaused || !visible) return false
  return intervalMs
}
