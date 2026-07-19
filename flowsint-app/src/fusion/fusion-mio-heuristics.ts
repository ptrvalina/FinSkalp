/** MIO analytical depth — client heuristics from existing payload (U7) */

import type { MioExecutableCard } from './fusion-mio-actions'

export function confidenceMeter(priority?: string): number {
  switch ((priority ?? 'medium').toLowerCase()) {
    case 'critical':
      return 0.92
    case 'high':
      return 0.78
    case 'low':
      return 0.45
    default:
      return 0.62
  }
}

export function buildConsequenceHint(card: MioExecutableCard): string {
  switch (card.actionKind) {
    case 'fuse':
      return 'если выполнить → OSINT Fusion, гипотезы и новые узлы на графе'
    case 'screen_wallet':
      return 'если выполнить → KYT-скрининг, обновление risk score на графе'
    case 'open_report':
      return 'если выполнить → SAR/PDF отчёт для подачи в регулятор'
    case 'transition':
      return card.targetStatus
        ? `если выполнить → workflow → ${card.targetStatus.replace(/_/g, ' ')}`
        : 'если выполнить → продвижение по STR pipeline'
    default:
      return 'если выполнить → изменение состояния расследования'
  }
}

export function inferHypothesisTag(card: MioExecutableCard): string | null {
  const text = `${card.title} ${card.rationale ?? ''}`.toLowerCase()
  if (/mixer|tumbler|layer/.test(text)) return 'структурирование'
  if (/sanction|ofac/.test(text)) return 'санкции'
  if (/exchange|cex/.test(text)) return 'обналичивание'
  if (/bridge|cross/.test(text)) return 'cross-chain'
  if (/evidence|доказ/.test(text)) return 'доказывание'
  if (/fusion|osint/.test(text)) return 'разведка'
  return null
}

export type MioContradiction = {
  cardA: string
  cardB: string
  reason: string
}

const STATUS_ORDER = [
  'new',
  'scoring',
  'fusion',
  'graph',
  'hypotheses',
  'evidence',
  'review',
  'recommendation',
  'filed',
]

function statusRank(status?: string | null): number {
  if (!status) return -1
  const idx = STATUS_ORDER.indexOf(status)
  return idx >= 0 ? idx : 0
}

/** Flag conflicting workflow transitions suggested by two MIO cards. */
export function detectMioContradictions(cards: MioExecutableCard[]): MioContradiction[] {
  const transitions = cards.filter(
    (c) => c.actionKind === 'transition' && c.targetStatus
  )
  const out: MioContradiction[] = []
  for (let i = 0; i < transitions.length; i++) {
    for (let j = i + 1; j < transitions.length; j++) {
      const a = transitions[i]!
      const b = transitions[j]!
      if (a.targetStatus !== b.targetStatus) {
        const rankA = statusRank(a.targetStatus)
        const rankB = statusRank(b.targetStatus)
        if (Math.abs(rankA - rankB) > 1) {
          out.push({
            cardA: a.id,
            cardB: b.id,
            reason: `Конфликт workflow: ${a.targetStatus} vs ${b.targetStatus}`,
          })
        }
      }
    }
  }
  const fuseCards = cards.filter((c) => c.actionKind === 'fuse')
  const reportCards = cards.filter((c) => c.actionKind === 'open_report')
  if (fuseCards.length && reportCards.length) {
    out.push({
      cardA: fuseCards[0]!.id,
      cardB: reportCards[0]!.id,
      reason: 'Fusion ещё не завершён, но рекомендуется отчёт',
    })
  }
  return out
}

export function pickPinnedCriticalCard(cards: MioExecutableCard[]): MioExecutableCard | null {
  return (
    cards.find((c) => c.priority === 'critical') ??
    cards.find((c) => c.priority === 'high') ??
    null
  )
}

/** Estimate STR filing probability for open_report / filing cards (client heuristic). */
export function estimateStrProbability(card: MioExecutableCard): number | null {
  if (card.actionKind !== 'open_report') return null
  const text = `${card.title} ${card.rationale ?? ''}`.toLowerCase()
  let base = 0.72
  if (card.priority === 'critical') base = 0.9
  else if (card.priority === 'high') base = 0.82
  else if (card.priority === 'low') base = 0.55
  if (/sanction|115|sar|регулятор|подач/.test(text)) base += 0.06
  if (/evidence|доказ/.test(text)) base += 0.04
  return Math.min(0.98, base)
}
