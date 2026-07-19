import { memo, useMemo } from 'react'



import { cn } from '@/lib/utils'



import type { MIOActionCard } from './FusionMIO'

import type { MioExecutableCard } from './fusion-mio-actions'

import {

  buildConsequenceHint,

  confidenceMeter,

  inferHypothesisTag,

  estimateStrProbability,

} from './fusion-mio-heuristics'

import { fusionCopy } from './fusion-copy'



type Props = {

  cards: MIOActionCard[]

  livePulse?: string | null

  canExecute?: boolean

  onExecute?: (card: MioExecutableCard) => void

  onDefer?: (cardId: string) => void

  onExecAll?: () => void

  onCancelBatch?: () => void

  batchRunning?: boolean

  batchProgress?: { current: number; total: number } | null

  className?: string

}



function groupIntoMissions(cards: MIOActionCard[]): Array<{ id: string; label: string; cards: MIOActionCard[] }> {

  const groups = new Map<string, MIOActionCard[]>()

  for (const card of cards) {

    const kind = (card as MioExecutableCard).actionKind ?? 'mission'

    const key =

      kind === 'run_scalpel' || kind === 'fuse'

        ? 'collect'

        : kind === 'screen_wallet'

          ? 'kyt'

          : kind === 'transition'

            ? 'workflow'

            : kind

    const list = groups.get(key) ?? []

    list.push(card)

    groups.set(key, list)

  }

  const labels = fusionCopy.mio.missionLabels

  return [...groups.entries()].map(([key, groupCards]) => ({

    id: key,

    label: labels[key] ?? labels.mission,

    cards: groupCards,

  }))

}



export const FusionMioMissionStrip = memo(function FusionMioMissionStrip({

  cards,

  livePulse,

  canExecute = true,

  onExecute,

  onDefer,

  onExecAll,

  onCancelBatch,

  batchRunning,

  batchProgress,

  className,

}: Props) {

  const missions = useMemo(() => groupIntoMissions(cards), [cards])

  const flatCards = useMemo(() => cards.slice(0, 8), [cards])



  if (!cards.length) {

    return (

      <div className={cn('fusion-mio-mission-strip', className)} data-testid="fusion-mio-mission-strip">

        <div className="fusion-mio-mission-strip__header">

          <span className="fusion-mio-mission-strip__title">{fusionCopy.mio.title}</span>

          <span className="fusion-mio-mission-strip__pulse">

            {livePulse ?? fusionCopy.mio.awaitingRecommendations}

          </span>

        </div>

      </div>

    )

  }



  return (

    <div className={cn('fusion-mio-mission-strip', className)} data-testid="fusion-mio-mission-strip">

      <div className="fusion-mio-mission-strip__header">

        <span className="fusion-mio-mission-strip__title">{fusionCopy.mio.titleShort}</span>

        <span className="fusion-mio-mission-strip__pulse">

          {livePulse ?? fusionCopy.mio.missionsSummary(missions.length, cards.length)}

        </span>

        {canExecute && onExecAll ? (

          <button

            type="button"

            className="fusion-mio-mission-card__btn fusion-mio-mission-card__btn--execute"

            disabled={batchRunning}

            onClick={() => onExecAll()}

          >

            {batchRunning

              ? batchProgress

                ? fusionCopy.mio.execProgress(batchProgress.current, batchProgress.total)

                : fusionCopy.mio.execAllRunning

              : fusionCopy.mio.execAll}

          </button>

        ) : null}

        {canExecute && batchRunning && onCancelBatch ? (

          <button

            type="button"

            className="fusion-mio-mission-card__btn"

            onClick={() => onCancelBatch()}

          >

            {fusionCopy.mio.batchCancel}

          </button>

        ) : null}

      </div>

      <div className="fusion-mio-mission-strip__missions">

        {flatCards.map((card) => {

          const execCard = card as MioExecutableCard

          const confidence = confidenceMeter(card.priority)

          const consequence = buildConsequenceHint(execCard)

          const hypothesis = inferHypothesisTag(execCard)
          const strProbability = estimateStrProbability(execCard)



          return (

            <div

              key={card.id}

              className={cn(

                'fusion-mio-mission-card',

                card.priority === 'critical' && 'fusion-mio-mission-card--critical'

              )}

            >

              <div className="fusion-mio-mission-card__meta">

                <span

                  className={cn(

                    'fusion-mio-mission-card__priority',

                    card.priority === 'critical' && 'fusion-tone-critical',

                    card.priority === 'high' && 'fusion-tone-warning'

                  )}

                >

                  {fusionCopy.mio.priority[card.priority ?? 'medium'] ?? fusionCopy.mio.priority.medium}

                </span>

                {hypothesis ? (

                  <span className="fusion-mio-mission-card__hypothesis">{hypothesis}</span>

                ) : null}

                {strProbability != null ? (

                  <span className="fusion-mio-mission-card__str" title={fusionCopy.mioBatch.strProbability}>

                    STR {Math.round(strProbability * 100)}%

                  </span>

                ) : null}

              </div>

              <p className="fusion-mio-mission-card__title">{card.title}</p>

              <div className="fusion-mio-mission-card__confidence" title={fusionCopy.mio.confidenceLabel}>

                <div

                  className="fusion-mio-mission-card__confidence-bar"

                  style={{ width: `${Math.round(confidence * 100)}%` }}

                />

                <span className="fusion-mio-mission-card__confidence-value">

                  {Math.round(confidence * 100)}%

                </span>

              </div>

              <p className="fusion-mio-mission-card__consequence">

                {fusionCopy.mio.consequencePrefix} {consequence}

              </p>

              <div className="fusion-mio-mission-card__actions">

                {canExecute && onExecute ? (

                  <button

                    type="button"

                    className="fusion-mio-mission-card__btn fusion-mio-mission-card__btn--execute"

                    onClick={() => onExecute(execCard)}

                  >

                    {fusionCopy.mio.exec}

                  </button>

                ) : null}

                {onDefer ? (

                  <button

                    type="button"

                    className="fusion-mio-mission-card__btn"

                    onClick={() => onDefer(card.id)}

                  >

                    {fusionCopy.mio.defer}

                  </button>

                ) : null}

              </div>

            </div>

          )

        })}

      </div>

    </div>

  )

})

