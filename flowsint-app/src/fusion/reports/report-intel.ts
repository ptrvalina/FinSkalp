import type { ReportCaseBundle } from './report-types'

type NodeRow = { id: string; kind?: string; label?: string; confidence?: number }
type EdgeRow = {
  id: string
  source: string
  target: string
  rel_type?: string
  strength?: number
}

export function reportNodes(bundle: ReportCaseBundle): NodeRow[] {
  return (bundle.graph?.nodes ?? []) as NodeRow[]
}

export function reportEdges(bundle: ReportCaseBundle): EdgeRow[] {
  return (bundle.graph?.edges ?? []) as EdgeRow[]
}

export function shortEntityLabel(raw?: string | null, max = 28): string {
  if (!raw) return '—'
  const cleaned = raw.replace(/^(wallet|osint_mention|platform):/, '').replace(/^tron:/i, '')
  if (cleaned.length <= max) return cleaned
  return `${cleaned.slice(0, Math.max(8, max - 3))}…`
}

/** Composite operator risk when fusion doesn't expose illegal_flow_score. */
export function deriveReportRisk(bundle: ReportCaseBundle): {
  score: number
  level: string
  source: string
  factors: Array<{ label: string; value: string }>
} {
  const fusion = bundle.fusion
  const hist = bundle.riskHistory.points.at(-1)?.score
  if (hist != null && Number.isFinite(hist)) {
    const score = Math.round(Number(hist))
    return {
      score,
      level: riskLevelFromScore(score),
      source: 'risk_history',
      factors: [{ label: 'Risk history', value: String(score) }],
    }
  }

  const illegal = Number(fusion?.illegal_flow_score ?? bundle.investigate?.risk_score)
  if (Number.isFinite(illegal) && illegal > 0) {
    const score = illegal <= 1 ? Math.round(illegal * 100) : Math.round(illegal)
    return {
      score,
      level: String(fusion?.risk_level ?? bundle.investigate?.risk_level ?? riskLevelFromScore(score)),
      source: 'fusion',
      factors: [{ label: 'Illegal flow score', value: String(score) }],
    }
  }

  const nodes = reportNodes(bundle)
  const edges = reportEdges(bundle)
  const hyp = (fusion?.hypotheses as Array<{ confidence?: number; statement_ru?: string }> | undefined) ?? []
  const hypConf = hyp.reduce((s, h) => s + (Number(h.confidence) || 0), 0) / Math.max(hyp.length, 1)
  const nodeConf =
    nodes.reduce((s, n) => s + (Number(n.confidence) || 0), 0) / Math.max(nodes.length, 1)
  const edgeStrength =
    edges.reduce((s, e) => s + (Number(e.strength) || 0.5), 0) / Math.max(edges.length, 1)
  const osintCount = nodes.filter((n) => (n.kind ?? '').toLowerCase().includes('osint')).length
  const density = nodes.length ? edges.length / nodes.length : 0
  const flagged = flaggedWallets(bundle)
  const sancCount = flagged.filter((w) => w.sanctioned).length
  const scamCount = flagged.filter((w) => w.scam).length
  const flaggedTransfers = sanctionedTransferEdges(bundle).length

  // Weighted composite 0–100 from available investigation signals
  const score = Math.round(
    Math.min(
      99,
      hypConf * 30 +
        nodeConf * 15 +
        edgeStrength * 12 +
        Math.min(osintCount, 15) * 1.0 +
        Math.min(density, 2) * 6 +
        Math.min(sancCount, 5) * 12 +
        Math.min(scamCount, 5) * 10 +
        Math.min(flaggedTransfers, 8) * 4
    )
  )

  return {
    score,
    level: riskLevelFromScore(score),
    source: 'derived',
    factors: [
      { label: 'Гипотезы (avg conf)', value: hyp.length ? `${Math.round(hypConf * 100)}%` : '—' },
      { label: 'Сущности (avg conf)', value: nodes.length ? `${Math.round(nodeConf * 100)}%` : '—' },
      { label: 'Сила связей', value: edges.length ? `${Math.round(edgeStrength * 100)}%` : '—' },
      { label: 'Санкционные кошельки', value: String(sancCount) },
      { label: 'Scam/Abuse кошельки', value: String(scamCount) },
      { label: 'Transfer → flagged', value: String(flaggedTransfers) },
      { label: 'OSINT mentions', value: String(osintCount) },
      { label: 'Граф', value: `${nodes.length}n / ${edges.length}e` },
    ],
  }
}

function riskLevelFromScore(score: number): string {
  if (score >= 80) return 'critical'
  if (score >= 60) return 'high'
  if (score >= 40) return 'medium'
  if (score >= 20) return 'low'
  return 'info'
}

export function monetaryEdges(bundle: ReportCaseBundle) {
  return reportEdges(bundle).filter((e) =>
    /TRANSFER|COUNTERPARTY|BRIDGE|PAYMENT/i.test(e.rel_type ?? '')
  )
}

export type RiskFlaggedWallet = {
  id: string
  label?: string
  address?: string
  confidence?: number
  sanctioned?: boolean
  scam?: boolean
  attribution?: string
  owner?: string
  owner_category?: string
  flags?: string[]
  risk_tags?: string[]
}

export function flaggedWallets(bundle: ReportCaseBundle): RiskFlaggedWallet[] {
  return reportNodes(bundle)
    .filter((n) => {
      const row = n as RiskFlaggedWallet
      return Boolean(
        row.sanctioned ||
          row.scam ||
          (row.flags ?? []).some((f) => /sanction|scam/i.test(f)) ||
          /SANCTION|SCAM/i.test(row.label ?? '')
      )
    })
    .map((n) => n as RiskFlaggedWallet)
}

export function attributedWallets(bundle: ReportCaseBundle): RiskFlaggedWallet[] {
  return reportNodes(bundle)
    .filter((n) => {
      const row = n as RiskFlaggedWallet & { kind?: string }
      if ((row.kind ?? '').toLowerCase() !== 'wallet') return false
      return Boolean(row.attribution || row.owner || row.owner_category)
    })
    .map((n) => n as RiskFlaggedWallet)
}

export function sanctionedTransferEdges(bundle: ReportCaseBundle) {
  return reportEdges(bundle).filter((e) => /SANCTION|SCAM/i.test(e.rel_type ?? ''))
}

export function deriveExecutiveSummary(bundle: ReportCaseBundle): string | null {
  const fusion = bundle.fusion
  if (fusion?.executive_summary_ru) return String(fusion.executive_summary_ru)
  if (bundle.investigate?.summary_ru) return String(bundle.investigate.summary_ru)

  const hyp = (fusion?.hypotheses as Array<{ statement_ru?: string; confidence?: number }> | undefined)?.[0]
  const nodes = reportNodes(bundle)
  const edges = reportEdges(bundle)
  const risk = deriveReportRisk(bundle)
  const wallets = walletNodes(bundle)
  const wallet = wallets[0]
  const counterparties = Math.max(0, wallets.length - 1)
  const transfers = monetaryEdges(bundle).length
  const flagged = flaggedWallets(bundle)
  const sanc = flagged.filter((w) => w.sanctioned).length
  const scam = flagged.filter((w) => w.scam).length
  const attributed = attributedWallets(bundle).length
  const osint = nodes.filter((n) => (n.kind ?? '').toLowerCase().includes('osint')).length

  if (!nodes.length && !hyp) return null

  const parts = [
    `Дело ${bundle.caseRef}: граф ${nodes.length} сущностей / ${edges.length} связей.`,
    wallet ? `Seed-кошелёк: ${shortEntityLabel(wallet.label ?? wallet.id, 40)}.` : null,
    counterparties
      ? `On-chain контрагенты: ${counterparties}; monetary links: ${transfers}.`
      : transfers
        ? `Monetary links: ${transfers}.`
        : null,
    sanc || scam
      ? `Флаги риска: санкции ${sanc}, scam/abuse ${scam}.`
      : null,
    attributed ? `Атрибутировано кошельков (биржа/VASP/субъект): ${attributed}.` : null,
    osint ? `OSINT-упоминания: ${osint}.` : null,
    hyp?.statement_ru
      ? `Гипотеза (${Math.round((hyp.confidence ?? 0) * 100)}%): ${hyp.statement_ru}`
      : null,
    `Оценка риска: ${risk.score}% (${risk.level}).`,
  ].filter(Boolean)

  return parts.join(' ')
}

export function osintMentionNodes(bundle: ReportCaseBundle): NodeRow[] {
  return reportNodes(bundle).filter((n) => {
    const kind = (n.kind ?? '').toLowerCase()
    return kind.includes('osint') || kind.includes('mention')
  })
}

export function walletNodes(bundle: ReportCaseBundle): NodeRow[] {
  return reportNodes(bundle).filter((n) => {
    const kind = (n.kind ?? '').toLowerCase()
    return kind.includes('wallet') || kind.includes('address') || /^T[A-Za-z0-9]{20,}/.test(n.label ?? '')
  })
}
