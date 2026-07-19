import { useCallback, useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'

import { cn } from '@/lib/utils'

import { FusionEmptyState } from './FusionEmptyState'
import { FusionInlineError } from './FusionInlineError'
import { FusionMioBriefingStrip, type MioBriefingContext } from './FusionMioBriefingStrip'
import { FusionPanel } from './FusionPanel'
import {
  getBatchDependencyHint,
  pickBriefingCards,
  runMioBatch,
  type BatchProgress,
} from './fusion-mio-batch'
import {
  buildConsequenceHint,
  confidenceMeter,
  detectMioContradictions,
  inferHypothesisTag,
  pickPinnedCriticalCard,
} from './fusion-mio-heuristics'
import type { MioExecutableCard } from './fusion-mio-actions'
import { useFusionAnnouncer } from './useFusionAnnouncer'

export type MIOActionCard = {
  id: string
  title: string
  rationale?: string
  priority?: 'critical' | 'high' | 'medium' | 'low'
  actions?: Array<{ id: string; label: string; variant?: 'execute' | 'defer' | 'dismiss' }>
}

type Props = {
  recommendations?: Array<{ action_ru?: string; priority?: string; explanation_ru?: string; rationale_ru?: string }>
  cards?: MIOActionCard[]
  onAction?: (cardId: string, actionId: string) => void
  /** Required for batch execute — runs a single card (same handler as EXECUTE). */
  onExecuteCard?: (card: MioExecutableCard) => Promise<void>
  briefing?: MioBriefingContext
  /** When false, EXECUTE and batch are hidden (read-only / viewer roles). */
  canExecute?: boolean
  lastRefreshedAt?: Date
  isRefreshing?: boolean
  className?: string
}

const PRIORITY_CLASS: Record<string, string> = {
  critical: 'fusion-tone-critical',
  high: 'fusion-tone-warning',
  medium: 'fusion-tone-caution',
  low: 'fusion-tone-ops',
}

function mapRecommendations(
  recs: Array<{ action_ru?: string; priority?: string; explanation_ru?: string; rationale_ru?: string }>
): MIOActionCard[] {
  return recs.map((rec, i) => ({
    id: `rec-${i}`,
    title: rec.action_ru ?? 'Recommended action',
    rationale: rec.explanation_ru ?? rec.rationale_ru,
    priority: (rec.priority as MIOActionCard['priority']) ?? 'medium',
    actions: [
      { id: 'execute', label: 'EXECUTE', variant: 'execute' },
      { id: 'defer', label: 'DEFER', variant: 'defer' },
      { id: 'dismiss', label: 'DISMISS', variant: 'dismiss' },
    ],
  }))
}

export function FusionMIO({
  recommendations = [],
  cards,
  onAction,
  onExecuteCard,
  briefing,
  canExecute = true,
  lastRefreshedAt,
  isRefreshing,
  className,
}: Props) {
  const { announce } = useFusionAnnouncer()
  const actionCards = useMemo(
    () => cards ?? mapRecommendations(recommendations),
    [cards, recommendations]
  )

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [batchRunning, setBatchRunning] = useState(false)
  const [batchProgress, setBatchProgress] = useState<BatchProgress | undefined>()
  const [cardErrors, setCardErrors] = useState<Record<string, string>>({})
  const [batchSummaryError, setBatchSummaryError] = useState<string | null>(null)

  useEffect(() => {
    setSelectedIds((prev) => {
      const valid = new Set(actionCards.map((c) => c.id))
      const next = new Set([...prev].filter((id) => valid.has(id)))
      if (next.size === 0 && actionCards.length > 0 && canExecute) {
        actionCards.forEach((c) => next.add(c.id))
      }
      return next
    })
  }, [actionCards, canExecute])

  const topBriefingCards = useMemo(() => pickBriefingCards(actionCards, 3), [actionCards])
  const pinnedCritical = useMemo(() => pickPinnedCriticalCard(actionCards), [actionCards])
  const contradictions = useMemo(() => detectMioContradictions(actionCards as MioExecutableCard[]), [actionCards])
  const contradictionCardIds = useMemo(() => {
    const ids = new Set<string>()
    for (const c of contradictions) {
      ids.add(c.cardA)
      ids.add(c.cardB)
    }
    return ids
  }, [contradictions])

  const dependencyHint = useMemo(() => {
    const selected = actionCards.filter((c) => selectedIds.has(c.id)) as MioExecutableCard[]
    return getBatchDependencyHint(selected)
  }, [actionCards, selectedIds])

  const toggleCardSelection = useCallback((cardId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(cardId)) next.delete(cardId)
      else next.add(cardId)
      return next
    })
  }, [])

  const handleSelectAll = useCallback(() => {
    setSelectedIds((prev) => {
      if (prev.size === actionCards.length) return new Set()
      return new Set(actionCards.map((c) => c.id))
    })
  }, [actionCards])

  const handleBatchExecute = useCallback(async () => {
    if (!canExecute || !onExecuteCard || batchRunning) return

    const selected = actionCards.filter((c) => selectedIds.has(c.id)) as MioExecutableCard[]
    if (!selected.length) {
      toast.error('No cards selected')
      announce('No MIO cards selected for batch execute', 'assertive')
      return
    }

    setBatchRunning(true)
    setBatchSummaryError(null)
    setCardErrors({})
    setBatchProgress({ current: 0, total: selected.length, cardId: '', label: '' })
    announce(`Batch execute started: ${selected.length} action${selected.length === 1 ? '' : 's'}`)

    try {
      const result = await runMioBatch(selected, onExecuteCard, (progress) => {
        setBatchProgress(progress)
        if (progress.label) {
          announce(`Executing ${progress.current} of ${progress.total}: ${progress.label}`)
        }
      })

      const nextErrors: Record<string, string> = {}
      for (const failure of result.failed) {
        nextErrors[failure.cardId] = failure.error
      }
      setCardErrors(nextErrors)

      if (result.failed.length === 0) {
        toast.success(`Batch complete — ${result.succeeded.length} action${result.succeeded.length === 1 ? '' : 's'}`)
        announce(
          `Batch complete: ${result.succeeded.length} action${result.succeeded.length === 1 ? '' : 's'} succeeded`
        )
      } else if (result.succeeded.length === 0) {
        const summary = `Batch failed — ${result.failed.length} error${result.failed.length === 1 ? '' : 's'}`
        setBatchSummaryError(summary)
        toast.error(summary)
        announce(summary, 'assertive')
      } else {
        const summary = `Partial batch — ${result.succeeded.length} ok, ${result.failed.length} failed`
        setBatchSummaryError(summary)
        toast.warning(summary)
        announce(summary, 'assertive')
      }

      setSelectedIds(new Set())
    } finally {
      setBatchRunning(false)
      setBatchProgress(undefined)
    }
  }, [actionCards, announce, batchRunning, canExecute, onExecuteCard, selectedIds])

  const handleCardAction = useCallback(
    async (card: MIOActionCard, actionId: string, actionVariant?: string) => {
      if (actionVariant === 'execute' && onExecuteCard && canExecute) {
        setCardErrors((prev) => {
          const next = { ...prev }
          delete next[card.id]
          return next
        })
        try {
          await onExecuteCard(card as MioExecutableCard)
          announce(`${card.title} completed`)
        } catch (err) {
          const msg = err instanceof Error ? err.message : 'Execution failed'
          setCardErrors((prev) => ({ ...prev, [card.id]: msg }))
          announce(`MIO error: ${msg}`, 'assertive')
        }
        return
      }
      onAction?.(card.id, actionId)
    },
    [announce, canExecute, onAction, onExecuteCard]
  )

  return (
    <FusionPanel id="fusion-mio" title="Офицер разведки" defaultPinned>
      {briefing ? (
        <FusionMioBriefingStrip
          context={briefing}
          topCards={topBriefingCards}
          pinnedCritical={pinnedCritical}
          contradictions={contradictions}
          selectedCount={selectedIds.size}
          totalCards={actionCards.length}
          canExecute={canExecute}
          batchRunning={batchRunning}
          batchProgress={batchProgress}
          dependencyHint={dependencyHint}
          batchSummaryError={batchSummaryError}
          lastRefreshedAt={lastRefreshedAt}
          isRefreshing={isRefreshing}
          onExecuteAll={() => void handleBatchExecute()}
          onSelectAll={handleSelectAll}
        />
      ) : null}
      <div className={cn('flex flex-col gap-2 p-2', className)}>
        {actionCards.length === 0 ? (
          <FusionEmptyState
            title="НЕТ РЕКОМЕНДАЦИЙ"
            description="Ожидание FUSION — офицер разведки предложит действия после анализа дела."
            className="py-6"
          />
        ) : (
          actionCards.map((card) => {
            const isSelected = selectedIds.has(card.id)
            const isActiveBatch = batchRunning && batchProgress?.cardId === card.id
            const execCard = card as MioExecutableCard
            const conf = confidenceMeter(card.priority)
            const consequence = buildConsequenceHint(execCard)
            const hypothesis = inferHypothesisTag(execCard)
            const hasContradiction = contradictionCardIds.has(card.id)

            return (
              <article
                key={card.id}
                className={cn(
                  'fusion-surface-deck p-2',
                  isSelected && canExecute && 'ring-1 ring-[var(--fusion-ops-blue)]/40',
                  isActiveBatch && 'opacity-80',
                  hasContradiction && 'ring-1 ring-[var(--fusion-ops-yellow)]/50'
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex min-w-0 items-start gap-1.5">
                    {canExecute ? (
                      <input
                        type="checkbox"
                        className="mt-0.5 h-3 w-3 shrink-0 accent-[var(--fusion-ops-blue)]"
                        checked={isSelected}
                        disabled={batchRunning}
                        onChange={() => toggleCardSelection(card.id)}
                        aria-label={`Select ${card.title}`}
                      />
                    ) : null}
                    <span
                      className={cn(
                        'fusion-text-micro',
                        PRIORITY_CLASS[card.priority ?? 'medium']
                      )}
                    >
                      {(card.priority ?? 'medium').toUpperCase()}
                    </span>
                    {hypothesis ? (
                      <span className="fusion-text-micro text-[var(--fusion-ops-cyan)]">
                        {hypothesis}
                      </span>
                    ) : null}
                  </div>
                  {isActiveBatch ? (
                    <span className="fusion-text-micro text-[var(--fusion-ops-blue)]">RUNNING</span>
                  ) : null}
                </div>
                <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-[var(--fusion-bg-deck)]">
                  <div
                    className="h-full bg-[var(--fusion-ops-blue)] transition-all"
                    style={{ width: `${Math.round(conf * 100)}%` }}
                    title={`Confidence ${Math.round(conf * 100)}%`}
                  />
                </div>
                <h4 className="mt-1 fusion-heading-panel text-[11px] normal-case tracking-normal">
                  {card.title}
                </h4>
                {card.rationale ? (
                  <p className="mt-1 fusion-text-data">{card.rationale}</p>
                ) : null}
                <p className="mt-1 fusion-text-micro text-[var(--fusion-text-tertiary)]">
                  {consequence}
                </p>
                {hasContradiction ? (
                  <p className="mt-1 fusion-text-micro fusion-tone-warning">
                    ⚠ Конфликт рекомендаций — проверьте workflow
                  </p>
                ) : null}
                {cardErrors[card.id] ? (
                  <FusionInlineError message={cardErrors[card.id]!} className="mt-2" />
                ) : null}
                <div className="mt-2 flex flex-wrap gap-1">
                  {(card.actions ?? [])
                    .filter((action) => canExecute || action.variant !== 'execute')
                    .map((action) => (
                      <button
                        key={action.id}
                        type="button"
                        className={cn(
                          'px-2 py-1 fusion-text-micro border border-[var(--fusion-border)] rounded-[var(--fusion-radius-sm)]',
                          action.variant === 'execute' && 'text-[var(--fusion-ops-blue)]',
                          action.variant === 'defer' && 'text-[var(--fusion-ops-yellow)]',
                          action.variant === 'dismiss' && 'text-[var(--fusion-text-tertiary)]'
                        )}
                        disabled={batchRunning}
                        onClick={() => void handleCardAction(card, action.id, action.variant)}
                      >
                        {action.label}
                      </button>
                    ))}
                  {!canExecute ? (
                    <span
                      className="px-2 py-1 fusion-text-micro text-[var(--fusion-text-tertiary)]"
                      title="Read-only role — EXECUTE disabled (API enforces RBAC)"
                    >
                      READ-ONLY
                    </span>
                  ) : null}
                </div>
              </article>
            )
          })
        )}
      </div>
    </FusionPanel>
  )
}
