import type { MIOActionCard } from './FusionMIO'
import { WORKFLOW_LABELS } from './fusion-mission-data'
import type { InvestigationSeed } from './fusion-investigation-seed'
import { normalizeWalletAddress } from './fusion-wallet-utils'

export type MioActionKind =
  | 'fuse'
  | 'run_scalpel'
  | 'transition'
  | 'screen_wallet'
  | 'open_report'
  | 'open_evidence'
  | 'refresh_graph'
  | 'focus_seed'

export type MioExecutableCard = MIOActionCard & {
  actionKind?: MioActionKind
  targetStatus?: string
  walletAddress?: string
  walletChain?: string
}

/** STR pipeline stages — display only (Mission Strip). */
const STR_STAGE_ADVANCE: Record<string, string> = {
  new: 'scoring',
  scoring: 'fusion',
  fusion: 'graph',
  graph: 'hypotheses',
  hypotheses: 'evidence',
  evidence: 'review',
  review: 'recommendation',
  recommendation: 'filed',
}

/** API-valid workflow_status values (PATCH /cases/{id}). */
export const API_WORKFLOW_ADVANCE: Record<string, string> = {
  new: 'investigating',
  triage: 'investigating',
  investigating: 'pending_filing',
  pending_filing: 'filed',
  filed: 'archived',
}

const STR_ONLY_STATUSES = new Set([
  'scoring',
  'fusion',
  'graph',
  'hypotheses',
  'evidence',
  'review',
  'recommendation',
])

const API_VALID_STATUSES = new Set([
  'new',
  'triage',
  'investigating',
  'pending_filing',
  'filed',
  'archived',
])

export function toApiWorkflowStatus(target?: string | null): string | undefined {
  if (!target) return undefined
  if (API_VALID_STATUSES.has(target)) return target
  if (STR_ONLY_STATUSES.has(target)) return 'investigating'
  return API_WORKFLOW_ADVANCE[target]
}

const RECOMMENDATION_KIND: Record<string, MioActionKind> = {
  run_collectors: 'run_scalpel',
  define_seed: 'focus_seed',
  review_evidence: 'open_evidence',
  build_graph: 'refresh_graph',
  explain_risk: 'open_evidence',
  advance_workflow: 'transition',
}

function inferActionKind(
  actionRu: string,
  workflowStatus?: string | null,
  fusionDone?: boolean
): MioActionKind {
  const lower = actionRu.toLowerCase()
  if (
    lower.includes('fusion') ||
    lower.includes('osint') ||
    lower.includes('склей') ||
    lower.includes('обогащ')
  ) {
    return 'fuse'
  }
  if (
    lower.includes('кошел') ||
    lower.includes('wallet') ||
    lower.includes('screen') ||
    lower.includes('скрининг')
  ) {
    return 'screen_wallet'
  }
  if (
    lower.includes('отчёт') ||
    lower.includes('отчет') ||
    lower.includes('report') ||
    lower.includes('sar') ||
    lower.includes('pdf') ||
    lower.includes('115')
  ) {
    return 'open_report'
  }
  if (lower.includes('доказатель') || lower.includes('evidence')) {
    return 'open_evidence'
  }
  if (lower.includes('граф') || lower.includes('graph')) {
    return 'refresh_graph'
  }
  if (lower.includes('seed') || lower.includes('объект расслед') || lower.includes('seed-')) {
    return 'focus_seed'
  }
  if (
    lower.includes('коллектор') ||
    lower.includes('сбор данных') ||
    lower.includes('автоматическ') ||
    lower.includes('scalpel')
  ) {
    return 'run_scalpel'
  }
  if (!fusionDone && (workflowStatus === 'new' || workflowStatus === 'scoring')) {
    return 'fuse'
  }
  return 'transition'
}

function resolveActionKind(
  rec: { id: string; action_ru: string },
  workflowStatus?: string | null,
  fusionDone?: boolean
): MioActionKind {
  return RECOMMENDATION_KIND[rec.id] ?? inferActionKind(rec.action_ru, workflowStatus, fusionDone)
}

export function buildMioCards(params: {
  recommendations: Array<{
    id: string
    action_ru: string
    explanation_ru: string
    priority: string
  }>
  workflowStatus?: string | null
  fusionDone?: boolean
  defaultWallet?: { address: string; chain?: string } | null
  investigationWallet?: { address: string; chain?: string } | null
  investigationSeed?: InvestigationSeed
  isDemoCase?: boolean
  /** Address already KYT-screened — hide duplicate screen card */
  lastKytAddress?: string | null
  /** Graph node count — used to offer Fusion mission when ready */
  nodeCountHint?: number
}): MioExecutableCard[] {
  const {
    recommendations,
    workflowStatus,
    fusionDone,
    defaultWallet,
    investigationWallet,
    isDemoCase,
    lastKytAddress,
    nodeCountHint = 0,
  } = params
  const seedWallet = investigationWallet ?? defaultWallet
  const apiNextStatus = workflowStatus ? API_WORKFLOW_ADVANCE[workflowStatus] : undefined
  const strNextStatus = workflowStatus ? STR_STAGE_ADVANCE[workflowStatus] : undefined

  const cards: MioExecutableCard[] = recommendations.map((rec) => {
    let actionKind = resolveActionKind(rec, workflowStatus, fusionDone)
    if (rec.id === 'run_collectors' && isDemoCase && !investigationWallet) {
      actionKind = 'fuse'
    }
    const walletForCard =
      actionKind === 'screen_wallet' || actionKind === 'run_scalpel' ? seedWallet : undefined
    return {
      id: rec.id,
      title: rec.action_ru,
      rationale: rec.explanation_ru,
      priority: (rec.priority as MioExecutableCard['priority']) ?? 'medium',
      actionKind,
      targetStatus: actionKind === 'transition' ? apiNextStatus : undefined,
      walletAddress: walletForCard?.address,
      walletChain: walletForCard?.chain,
      actions: [
        { id: 'execute', label: 'EXECUTE', variant: 'execute' },
        { id: 'defer', label: 'DEFER', variant: 'defer' },
        { id: 'dismiss', label: 'DISMISS', variant: 'dismiss' },
      ],
    }
  })

  if (seedWallet && !cards.some((c) => c.id === 'screen_wallet')) {
    const alreadyScreened =
      Boolean(lastKytAddress) &&
      normalizeWalletAddress(lastKytAddress!) === normalizeWalletAddress(seedWallet.address)
    if (!alreadyScreened && !fusionDone) {
      cards.unshift({
        id: 'screen_wallet',
        title: 'Проверить кошелёк (KYT / скрининг)',
        rationale: `Seed-кошелёк ${seedWallet.address.slice(0, 12)}… — on-chain, санкции, risk score`,
        priority: 'critical',
        actionKind: 'screen_wallet',
        walletAddress: seedWallet.address,
        walletChain: seedWallet.chain,
        actions: [
          { id: 'execute', label: 'EXECUTE', variant: 'execute' },
          { id: 'defer', label: 'DEFER', variant: 'defer' },
          { id: 'dismiss', label: 'DISMISS', variant: 'dismiss' },
        ],
      })
    }
  }

  if (!fusionDone && nodeCountHint > 0 && !cards.some((c) => c.actionKind === 'fuse')) {
    cards.push({
      id: 'run_fusion',
      title: 'Запустить OSINT Fusion',
      rationale: 'Следующий обязательный этап после графа и KYT — склейка доказательств и гипотез',
      priority: 'high',
      actionKind: 'fuse',
      actions: [
        { id: 'execute', label: 'EXECUTE', variant: 'execute' },
        { id: 'defer', label: 'DEFER', variant: 'defer' },
      ],
    })
  }

  if (!cards.length && workflowStatus) {
    const kind: MioActionKind =
      !fusionDone && (workflowStatus === 'new' || workflowStatus === 'scoring')
        ? 'fuse'
        : workflowStatus === 'pending_filing' || workflowStatus === 'filed'
          ? 'open_report'
          : 'transition'
    cards.push({
      id: 'workflow-next',
      title:
        kind === 'fuse'
          ? 'Запустить OSINT Fusion'
          : kind === 'open_report'
            ? 'Открыть отчёт PDF'
            : `Перейти к этапу ${WORKFLOW_LABELS[strNextStatus ?? ''] ?? strNextStatus ?? '—'}`,
      rationale: 'Следующий шаг по статусу workflow',
      priority: 'high',
      actionKind: kind,
      targetStatus: kind === 'transition' ? apiNextStatus : undefined,
      walletAddress: seedWallet?.address,
      actions: [
        { id: 'execute', label: 'EXECUTE', variant: 'execute' },
        { id: 'defer', label: 'DEFER', variant: 'defer' },
      ],
    })
  }

  if (fusionDone && !cards.some((c) => c.actionKind === 'open_report')) {
    cards.unshift({
      id: 'open_report_center',
      title: 'Открыть Report Center',
      rationale: 'Fusion завершён — сформируйте или откройте отчёт 115-ФЗ',
      priority: 'high',
      actionKind: 'open_report',
      actions: [{ id: 'execute', label: 'OPEN', variant: 'execute' }],
    })
  }

  return cards.filter((c) => {
    if (fusionDone && (c.actionKind === 'screen_wallet' || c.actionKind === 'run_scalpel')) {
      return false
    }
    if (c.actionKind !== 'screen_wallet' || !lastKytAddress || !seedWallet) return true
    return normalizeWalletAddress(lastKytAddress) !== normalizeWalletAddress(seedWallet.address)
  })
}

export function extractDefaultWallet(
  graph?: { nodes?: Array<{ kind?: string; label?: string; id?: string }> } | null
): { address: string; chain?: string } | null {
  if (!graph?.nodes?.length) return null
  for (const node of graph.nodes) {
    const kind = (node.kind ?? '').toLowerCase()
    const raw = (node.label ?? node.id ?? '').split('\n')[0]
    if (!(kind.includes('wallet') || kind.includes('address') || /^T[A-Za-z0-9]{20,}/.test(raw))) {
      continue
    }
    let address = raw
    let chain: string | undefined = kind.includes('tron')
      ? 'tron'
      : kind.includes('eth')
        ? 'eth'
        : undefined
    // primary_key / label may be "tron:T…"
    const m = address.match(/^(tron|eth|btc|bsc):(.+)$/i)
    if (m) {
      chain = m[1]!.toLowerCase()
      address = m[2]!
    }
    if (address.startsWith('wallet:')) {
      const rest = address.slice('wallet:'.length)
      const m2 = rest.match(/^(tron|eth|btc|bsc):(.+)$/i)
      if (m2) {
        chain = m2[1]!.toLowerCase()
        address = m2[2]!
      } else {
        address = rest
      }
    }
    return { address, chain }
  }
  return null
}
