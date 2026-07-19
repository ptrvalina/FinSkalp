import type { ReportCaseBundle, ReportModuleId } from './report-types'
import {
  attributedWallets,
  deriveExecutiveSummary,
  deriveReportRisk,
  flaggedWallets,
  osintMentionNodes,
  reportEdges,
  reportNodes,
  sanctionedTransferEdges,
  shortEntityLabel,
  walletNodes,
} from './report-intel'

export type ModuleFinding = {
  title: string
  detail: string
  tone?: 'critical' | 'ops' | 'muted'
}

/** Unique analytic bullets per report module — never reuse the same template block. */
export function buildModuleFindings(
  moduleId: ReportModuleId,
  bundle: ReportCaseBundle
): ModuleFinding[] {
  const nodes = reportNodes(bundle)
  const edges = reportEdges(bundle)
  const wallets = walletNodes(bundle)
  const mentions = osintMentionNodes(bundle)
  const risk = deriveReportRisk(bundle)
  const transfers = edges.filter((e) =>
    /TRANSFER|COUNTERPARTY|bridge/i.test(e.rel_type ?? '')
  )
  const osintEdges = edges.filter((e) => /OSINT/i.test(e.rel_type ?? ''))
  const seed = wallets[0]
  const cps = wallets.filter((w) => w.id !== seed?.id)
  const flagged = flaggedWallets(bundle)
  const attributed = attributedWallets(bundle)
  const flaggedTx = sanctionedTransferEdges(bundle)
  const sancN = flagged.filter((w) => w.sanctioned).length
  const scamN = flagged.filter((w) => w.scam).length

  switch (moduleId) {
    case 'executive-brief':
    case 'executive-summary':
      return [
        {
          title: 'Вердикт',
          detail: deriveExecutiveSummary(bundle) ?? 'Недостаточно данных — перезапустите Collect.',
          tone: 'critical',
        },
        {
          title: 'Риск',
          detail: `${risk.score}% · ${risk.level} (источник: ${risk.source})`,
          tone: 'critical',
        },
        {
          title: 'Санкции / Scam',
          detail: `санкции ${sancN} · scam ${scamN} · flagged transfers ${flaggedTx.length}`,
          tone: flagged.length || flaggedTx.length ? 'critical' : 'muted',
        },
        {
          title: 'Сеть',
          detail: `${nodes.length} сущностей · ${edges.length} связей · ${cps.length} контрагентов · атрибуция ${attributed.length}`,
          tone: 'ops',
        },
      ]
    case 'money-flow':
      return [
        {
          title: 'Движение средств',
          detail: transfers.length
            ? `${transfers.length} transfer/counterparty рёбер; ${cps.length} адресатов/источников`
            : 'Нет TRANSFER_* в графе — нужен onchain_explorer (Collect · Авто).',
          tone: transfers.length ? 'critical' : 'muted',
        },
        {
          title: 'На flagged',
          detail: flaggedTx.length
            ? `${flaggedTx.length} переводов на санкционные/scam кошельки`
            : 'Переводов на sanctioned/scam контрагентов не обнаружено',
          tone: flaggedTx.length ? 'critical' : 'ops',
        },
        {
          title: 'Топ контрагенты',
          detail:
            cps
              .slice(0, 5)
              .map((w) => shortEntityLabel(w.label ?? w.id, 24))
              .join(' · ') || '—',
          tone: 'ops',
        },
      ]
    case 'wallet-intelligence':
    case 'kyt':
      return [
        {
          title: 'Кошелёк',
          detail: seed
            ? `${shortEntityLabel(seed.label ?? seed.id, 42)} · conf ${seed.confidence != null ? Math.round(seed.confidence * 100) : '—'}%`
            : 'Seed wallet не найден',
          tone: 'ops',
        },
        {
          title: 'Атрибуция',
          detail: attributed.length
            ? attributed
                .slice(0, 4)
                .map((w) => w.attribution ?? w.owner ?? shortEntityLabel(w.label, 20))
                .join(' · ')
            : 'Биржа/организация не определена для seed/CPs',
          tone: attributed.length ? 'ops' : 'muted',
        },
        {
          title: 'Санкции / Scam',
          detail: `HIT ${flagged.length} · transfers ${flaggedTx.length}`,
          tone: flagged.length ? 'critical' : 'muted',
        },
        {
          title: 'KYT / риск',
          detail: `${risk.score}% · ${risk.level}`,
          tone: 'critical',
        },
      ]
    case 'attribution':
      return [
        {
          title: 'Владельцы / теги',
          detail: attributed.length
            ? `${attributed.length} кошельков с attribution`
            : 'Нет совпадений с CEX / VASP / person tags',
          tone: attributed.length ? 'ops' : 'muted',
        },
        {
          title: 'Примеры',
          detail:
            attributed
              .slice(0, 5)
              .map((w) => `${shortEntityLabel(w.address ?? w.label, 16)}→${w.attribution ?? w.owner}`)
              .join(' · ') || '—',
        },
      ]
    case 'osint-intelligence':
      return [
        {
          title: 'OSINT mentions',
          detail: `${mentions.length} упоминаний · ${osintEdges.length} OSINT_MENTION рёбер`,
          tone: mentions.length ? 'ops' : 'muted',
        },
        {
          title: 'Доказательства',
          detail: `${bundle.evidence.count} ECC-артефактов · timeline ${bundle.timeline.count}`,
        },
      ]
    case 'evidence-dossier':
    case 'chain-of-custody':
      return [
        {
          title: 'Evidence chain',
          detail: bundle.evidence.count
            ? `${bundle.evidence.count} артефактов с хешами`
            : 'Доказательства не зарегистрированы — seed/collect не создал ECC.',
          tone: bundle.evidence.count ? 'ops' : 'muted',
        },
      ]
    case 'aml':
    case 'risk-assessment':
      return [
        {
          title: 'AML индикаторы',
          detail: `Risk ${risk.score}% · transfers ${transfers.length} · sanctions ${sancN} · scam ${scamN}`,
          tone: 'critical',
        },
        ...risk.factors.slice(0, 4).map((f) => ({
          title: f.label,
          detail: f.value,
        })),
      ]
    case 'entity-profile':
    case 'relationship':
    case 'graph-intelligence':
      return [
        {
          title: 'Профиль сети',
          detail: `${nodes.length} nodes · ${edges.length} edges · kinds: ${summarizeKinds(nodes)}`,
          tone: 'ops',
        },
        {
          title: 'Связи',
          detail: summarizeRels(edges),
        },
        {
          title: 'Атрибуция',
          detail: `${attributed.length} labeled wallets`,
          tone: attributed.length ? 'ops' : 'muted',
        },
      ]
    case 'case-overview':
      return [
        {
          title: 'Статус дела',
          detail: `status=${String(bundle.caseRow?.status ?? '—')} · workflow=${String(bundle.caseRow?.workflow_status ?? '—')}`,
        },
        {
          title: 'Объём',
          detail: `graph ${nodes.length}/${edges.length} · evidence ${bundle.evidence.count} · timeline ${bundle.timeline.count}`,
        },
      ]
    case 'complete-investigation':
      return [
        {
          title: 'Итог расследования',
          detail: deriveExecutiveSummary(bundle) ?? '—',
          tone: 'critical',
        },
        {
          title: 'On-chain',
          detail: `${cps.length} контрагентов · ${transfers.length} monetary links · flagged ${flaggedTx.length}`,
          tone: 'ops',
        },
        {
          title: 'Санкции / Scam / Attribution',
          detail: `sanc ${sancN} · scam ${scamN} · owners ${attributed.length}`,
          tone: flagged.length || attributed.length ? 'critical' : 'muted',
        },
      ]
    default:
      return [
        {
          title: 'Данные модуля',
          detail: `${nodes.length} сущностей · ${edges.length} связей · risk ${risk.score}% · flagged ${flagged.length}`,
          tone: 'ops',
        },
      ]
  }
}

function summarizeKinds(nodes: Array<{ kind?: string }>): string {
  const m = new Map<string, number>()
  for (const n of nodes) {
    const k = n.kind ?? '?'
    m.set(k, (m.get(k) ?? 0) + 1)
  }
  return [...m.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([k, c]) => `${k}:${c}`)
    .join(', ')
}

function summarizeRels(edges: Array<{ rel_type?: string }>): string {
  const m = new Map<string, number>()
  for (const e of edges) {
    const k = e.rel_type ?? '?'
    m.set(k, (m.get(k) ?? 0) + 1)
  }
  return (
    [...m.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([k, c]) => `${k}×${c}`)
      .join(' · ') || 'нет рёбер'
  )
}
