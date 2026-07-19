import type { ReportCaseBundle, ReportModuleDef, ReportSectionId } from './report-types'
import { ReportMoneyFlowChart, ReportRiskHeatmap } from './ReportCharts'
import { ReportGraphSnapshot } from './ReportGraphSnapshot'
import {
  attributedWallets,
  deriveExecutiveSummary,
  deriveReportRisk,
  flaggedWallets,
  monetaryEdges,
  osintMentionNodes,
  reportEdges,
  reportNodes,
  sanctionedTransferEdges,
  shortEntityLabel,
  walletNodes,
} from './report-intel'

type EvidenceRow = { id: string; source_type?: string; content_hash?: string; status?: string }
type TimelineRow = { id: string; event_type: string; occurred_at: string; actor?: string }

function nodes(bundle: ReportCaseBundle) {
  return reportNodes(bundle)
}

function edges(bundle: ReportCaseBundle) {
  return reportEdges(bundle)
}

function fmtDate(iso?: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('ru-RU')
  } catch {
    return iso
  }
}

export function ReportCover({
  module,
  bundle,
}: {
  module: ReportModuleDef
  bundle: ReportCaseBundle
}) {
  return (
    <section className="fusion-report-doc__cover" id="section-cover">
      <div className="fusion-report-doc__classification">CONFIDENTIAL · FINANCIAL INTELLIGENCE</div>
      <h1 className="fusion-report-doc__title">{module.labelRu}</h1>
      <p className="fusion-report-doc__subtitle">{module.label}</p>
      <div className="fusion-report-doc__cover-meta">
        <div>
          <span className="label">CASE REF</span>
          <span className="value fusion-mono">{bundle.caseRef}</span>
        </div>
        <div>
          <span className="label">GENERATED</span>
          <span className="value">{fmtDate(new Date().toISOString())}</span>
        </div>
        <div>
          <span className="label">CLASSIFICATION</span>
          <span className="value">INTERNAL USE ONLY</span>
        </div>
      </div>
      <div className="fusion-report-doc__seal">ФС</div>
    </section>
  )
}

export function ReportSectionBody({
  sectionId,
  bundle,
}: {
  sectionId: ReportSectionId
  bundle: ReportCaseBundle
}) {
  const fusion = bundle.fusion

  switch (sectionId) {
    case 'cover':
      return null
    case 'classification':
      return (
        <section className="fusion-report-doc__section" id={`section-${sectionId}`}>
          <h2>Classification</h2>
          <p className="fusion-text-micro">
            Document prepared by FinSkalp Financial Intelligence Operating System. Distribution limited
            to authorized analysts and compliance officers.
          </p>
        </section>
      )
    case 'metadata':
      return (
        <section className="fusion-report-doc__section" id={`section-${sectionId}`}>
          <h2>Metadata</h2>
          <table className="fusion-report-doc__table">
            <tbody>
              <tr>
                <th>Case ID</th>
                <td className="fusion-mono">{bundle.caseId ?? '—'}</td>
              </tr>
              <tr>
                <th>Workflow</th>
                <td>{String(bundle.caseRow?.workflow_status ?? '—')}</td>
              </tr>
              <tr>
                <th>Priority</th>
                <td>{String(bundle.caseRow?.priority ?? '—')}</td>
              </tr>
              <tr>
                <th>Report module</th>
                <td>{bundle.caseRef}</td>
              </tr>
            </tbody>
          </table>
        </section>
      )
    case 'case-info': {
      const risk = deriveReportRisk(bundle)
      return (
        <section className="fusion-report-doc__section" id={`section-${sectionId}`}>
          <h2>Case Information</h2>
          <table className="fusion-report-doc__table">
            <tbody>
              <tr>
                <th>Status</th>
                <td>{String(bundle.caseRow?.status ?? '—')}</td>
              </tr>
              <tr>
                <th>Investigation ID</th>
                <td className="fusion-mono">{String(bundle.caseRow?.investigation_id ?? '—')}</td>
              </tr>
              <tr>
                <th>SLA breached</th>
                <td>{bundle.caseRow?.sla_breached ? 'YES' : 'NO'}</td>
              </tr>
              <tr>
                <th>Graph</th>
                <td>
                  {nodes(bundle).length} nodes · {edges(bundle).length} edges
                </td>
              </tr>
              <tr>
                <th>Risk</th>
                <td className="fusion-tone-critical">
                  {risk.score}% · {risk.level}
                </td>
              </tr>
            </tbody>
          </table>
        </section>
      )
    }
    case 'executive-summary': {
      const summary = deriveExecutiveSummary(bundle)
      const hyp =
        (fusion?.hypotheses as Array<{ statement_ru?: string; confidence?: number }> | undefined) ?? []
      return (
        <section className="fusion-report-doc__section" id={`section-${sectionId}`}>
          <h2>Executive Summary</h2>
          {summary ? (
            <p className="fusion-report-doc__prose">{summary}</p>
          ) : (
            <p className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
              Executive summary unavailable — complete Collect / Fusion for this case.
            </p>
          )}
          {hyp.length ? (
            <ul className="fusion-report-doc__list mt-3">
              {hyp.slice(0, 5).map((h, i) => (
                <li key={i}>
                  <strong>{Math.round((h.confidence ?? 0) * 100)}%</strong> — {h.statement_ru ?? '—'}
                </li>
              ))}
            </ul>
          ) : null}
          {bundle.investigate?.sar_report ? (
            <div className="fusion-report-doc__sar-block mt-4">
              <h3 className="fusion-text-micro uppercase text-[var(--fusion-text-tertiary)]">SAR narrative</h3>
              <pre className="fusion-mono fusion-text-micro whitespace-pre-wrap">
                {JSON.stringify(bundle.investigate.sar_report, null, 2).slice(0, 2400)}
              </pre>
            </div>
          ) : null}
        </section>
      )
    }
    case 'mission-summary':
      return (
        <section className="fusion-report-doc__section" id={`section-${sectionId}`}>
          <h2>Mission Summary</h2>
          <ul className="fusion-report-doc__list">
            <li>Evidence artifacts: {bundle.evidence.count}</li>
            <li>Graph entities: {nodes(bundle).length}</li>
            <li>Timeline events: {bundle.timeline.count}</li>
            <li>Cross-case links: {bundle.crossCase.count}</li>
          </ul>
        </section>
      )
    case 'network-overview': {
      const kinds = new Map<string, number>()
      for (const n of nodes(bundle)) {
        const k = n.kind ?? 'unknown'
        kinds.set(k, (kinds.get(k) ?? 0) + 1)
      }
      const top = [...kinds.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8)
      return (
        <section className="fusion-report-doc__section" id={`section-${sectionId}`}>
          <h2>Network Overview</h2>
          {top.length ? (
            <table className="fusion-report-doc__table">
              <thead>
                <tr>
                  <th>Kind</th>
                  <th>Count</th>
                </tr>
              </thead>
              <tbody>
                {top.map(([k, c]) => (
                  <tr key={k}>
                    <td>{k}</td>
                    <td>{c}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="fusion-text-micro text-[var(--fusion-text-tertiary)]">No graph data.</p>
          )}
        </section>
      )
    }
    case 'graph-snapshot':
      return (
        <section className="fusion-report-doc__section" id={`section-${sectionId}`}>
          <h2>Graph Snapshot</h2>
          <div className="fusion-report-doc__graph-stats">
            <div>
              <span className="stat">{nodes(bundle).length}</span>
              <span className="label">NODES</span>
            </div>
            <div>
              <span className="stat">{edges(bundle).length}</span>
              <span className="label">EDGES</span>
            </div>
          </div>
          <ReportGraphSnapshot bundle={bundle} />
        </section>
      )
    case 'entity-table': {
      const sorted = [...nodes(bundle)].sort((a, b) => {
        const rank = (k?: string) => {
          const x = (k ?? '').toLowerCase()
          if (x.includes('wallet')) return 0
          if (x.includes('platform') || x.includes('vasp') || x.includes('registry')) return 1
          if (x.includes('osint')) return 3
          return 2
        }
        return rank(a.kind) - rank(b.kind)
      })
      return (
        <section className="fusion-report-doc__section" id={`section-${sectionId}`}>
          <h2>Entity Table</h2>
          {sorted.length ? (
            <div className="fusion-report-doc__table-wrap">
              <table className="fusion-report-doc__table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Kind</th>
                    <th>Label / Owner</th>
                    <th>Flags</th>
                    <th>Conf.</th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.slice(0, 60).map((n) => {
                    const row = n as {
                      id: string
                      kind?: string
                      label?: string
                      confidence?: number
                      attribution?: string
                      owner?: string
                      sanctioned?: boolean
                      scam?: boolean
                      flags?: string[]
                    }
                    const flags = [
                      row.sanctioned ? 'SANCTIONS' : null,
                      row.scam ? 'SCAM' : null,
                      ...(row.flags ?? []),
                    ].filter(Boolean)
                    return (
                      <tr key={n.id}>
                        <td className="fusion-mono fusion-truncate max-w-[140px]">{n.id}</td>
                        <td>{n.kind ?? '—'}</td>
                        <td className="fusion-truncate max-w-[220px]">
                          {row.attribution || row.owner || n.label || '—'}
                        </td>
                        <td className={flags.length ? 'fusion-tone-critical' : undefined}>
                          {flags.join(' · ') || '—'}
                        </td>
                        <td>{n.confidence != null ? `${Math.round(n.confidence * 100)}%` : '—'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="fusion-text-micro text-[var(--fusion-text-tertiary)]">No entities on graph.</p>
          )}
        </section>
      )
    }
    case 'relationship-table': {
      const byId = new Map(nodes(bundle).map((n) => [n.id, n]))
      const rows = [...edges(bundle)].sort((a, b) => {
        const score = (t?: string) => (/TRANSFER|COUNTERPARTY/i.test(t ?? '') ? 0 : /OSINT/i.test(t ?? '') ? 2 : 1)
        return score(a.rel_type) - score(b.rel_type)
      })
      return (
        <section className="fusion-report-doc__section" id={`section-${sectionId}`}>
          <h2>Relationship Table</h2>
          {rows.length ? (
            <div className="fusion-report-doc__table-wrap">
              <table className="fusion-report-doc__table">
                <thead>
                  <tr>
                    <th>Source</th>
                    <th>Type</th>
                    <th>Target</th>
                    <th>Strength</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.slice(0, 60).map((e) => (
                    <tr key={e.id}>
                      <td title={e.source}>
                        {shortEntityLabel(byId.get(e.source)?.label ?? e.source, 32)}
                      </td>
                      <td className="fusion-mono">{e.rel_type ?? '—'}</td>
                      <td title={e.target}>
                        {shortEntityLabel(byId.get(e.target)?.label ?? e.target, 32)}
                      </td>
                      <td>
                        {e.strength != null ? `${Math.round(Number(e.strength) * 100)}%` : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="fusion-text-micro text-[var(--fusion-text-tertiary)]">No relationships.</p>
          )}
        </section>
      )
    }
    case 'timeline':
      return (
        <section className="fusion-report-doc__section" id={`section-${sectionId}`}>
          <h2>Timeline</h2>
          {bundle.timeline.count ? (
            <ol className="fusion-report-doc__timeline">
              {(bundle.timeline.events as TimelineRow[]).slice(0, 40).map((ev) => (
                <li key={ev.id}>
                  <time>{fmtDate(ev.occurred_at)}</time>
                  <strong>{ev.event_type}</strong>
                  <span>{ev.actor ?? '—'}</span>
                </li>
              ))}
            </ol>
          ) : (
            <p className="fusion-text-micro text-[var(--fusion-text-tertiary)]">No timeline events.</p>
          )}
        </section>
      )
    case 'evidence':
      return (
        <section className="fusion-report-doc__section" id={`section-${sectionId}`}>
          <h2>Evidence</h2>
          {bundle.evidence.count ? (
            <table className="fusion-report-doc__table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Source</th>
                  <th>Hash</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {(bundle.evidence.items as EvidenceRow[]).slice(0, 40).map((ev) => (
                  <tr key={ev.id}>
                    <td className="fusion-mono">{ev.id.slice(0, 12)}…</td>
                    <td>{ev.source_type ?? '—'}</td>
                    <td className="fusion-mono fusion-truncate max-w-[160px]">
                      {ev.content_hash?.slice(0, 16) ?? '—'}…
                    </td>
                    <td>{ev.status ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="fusion-text-micro text-[var(--fusion-text-tertiary)]">No evidence registered.</p>
          )}
        </section>
      )
    case 'wallet-profile': {
      const wallets = walletNodes(bundle)
      const risk = deriveReportRisk(bundle)
      return (
        <section className="fusion-report-doc__section" id={`section-${sectionId}`}>
          <h2>Wallet Profile</h2>
          {wallets.length ? (
            <table className="fusion-report-doc__table">
              <thead>
                <tr>
                  <th>Address</th>
                  <th>Kind</th>
                  <th>Conf.</th>
                  <th>Links</th>
                </tr>
              </thead>
              <tbody>
                {wallets.map((w) => {
                  const degree = edges(bundle).filter(
                    (e) => e.source === w.id || e.target === w.id
                  ).length
                  return (
                    <tr key={w.id}>
                      <td className="fusion-mono">{shortEntityLabel(w.label ?? w.id, 44)}</td>
                      <td>{w.kind ?? 'wallet'}</td>
                      <td>{w.confidence != null ? `${Math.round(w.confidence * 100)}%` : '—'}</td>
                      <td>{degree}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          ) : (
            <p className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
              Кошелёк не найден в графе — добавьте seed и запустите Collect.
            </p>
          )}
          <table className="fusion-report-doc__table mt-4">
            <tbody>
              <tr>
                <th>Risk score</th>
                <td className="fusion-tone-critical">{risk.score}%</td>
              </tr>
              <tr>
                <th>Risk level</th>
                <td>{risk.level}</td>
              </tr>
              <tr>
                <th>Source</th>
                <td>{risk.source}</td>
              </tr>
            </tbody>
          </table>
        </section>
      )
    }
    case 'money-flow': {
      const bridges = (fusion?.bridges as Array<Record<string, unknown>> | undefined) ?? []
      const transfers = monetaryEdges(bundle)
      const byId = new Map(nodes(bundle).map((n) => [n.id, n]))
      const wallets = walletNodes(bundle)
      const seed = wallets[0]
      const cps = wallets.filter((w) => w.id !== seed?.id)
      const byType = new Map<string, number>()
      for (const e of transfers) {
        const t = e.rel_type ?? '?'
        byType.set(t, (byType.get(t) ?? 0) + 1)
      }
      return (
        <section className="fusion-report-doc__section" id={`section-${sectionId}`}>
          <h2>Money Flow / Link Flow</h2>
          <div className="fusion-report-doc__graph-stats">
            <div>
              <span className="stat">{transfers.length}</span>
              <span className="label">MONETARY LINKS</span>
            </div>
            <div>
              <span className="stat">{cps.length}</span>
              <span className="label">COUNTERPARTIES</span>
            </div>
            <div>
              <span className="stat">{[...byType.entries()].map(([k, c]) => `${k}×${c}`).join(' ') || '—'}</span>
              <span className="label">BY TYPE</span>
            </div>
          </div>
          <ReportMoneyFlowChart bundle={bundle} />
          <ReportGraphSnapshot bundle={bundle} height={220} />
          {transfers.length ? (
            <div className="fusion-report-doc__table-wrap mt-4">
              <h3 className="fusion-text-micro uppercase text-[var(--fusion-text-tertiary)] mb-2">
                Transfer / Counterparty edges
              </h3>
              <table className="fusion-report-doc__table">
                <thead>
                  <tr>
                    <th>From</th>
                    <th>Type</th>
                    <th>To</th>
                    <th>Strength</th>
                  </tr>
                </thead>
                <tbody>
                  {transfers.slice(0, 40).map((e) => (
                    <tr key={e.id}>
                      <td title={e.source}>
                        {shortEntityLabel(byId.get(e.source)?.label ?? e.source, 28)}
                      </td>
                      <td className="fusion-mono">{e.rel_type}</td>
                      <td title={e.target}>
                        {shortEntityLabel(byId.get(e.target)?.label ?? e.target, 28)}
                      </td>
                      <td>
                        {e.strength != null ? `${Math.round(Number(e.strength) * 100)}%` : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
          {cps.length ? (
            <div className="fusion-report-doc__table-wrap mt-4">
              <h3 className="fusion-text-micro uppercase text-[var(--fusion-text-tertiary)] mb-2">
                Counterparties ({cps.length})
              </h3>
              <table className="fusion-report-doc__table">
                <thead>
                  <tr>
                    <th>Address</th>
                    <th>Conf.</th>
                    <th>Degree</th>
                  </tr>
                </thead>
                <tbody>
                  {cps.slice(0, 30).map((w) => {
                    const degree = edges(bundle).filter(
                      (e) => e.source === w.id || e.target === w.id
                    ).length
                    return (
                      <tr key={w.id}>
                        <td className="fusion-mono">{shortEntityLabel(w.label ?? w.id, 44)}</td>
                        <td>{w.confidence != null ? `${Math.round(w.confidence * 100)}%` : '—'}</td>
                        <td>{degree}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ) : null}
          {bridges.length ? (
            <table className="fusion-report-doc__table mt-4">
              <thead>
                <tr>
                  <th>Fusion bridge</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {bridges.slice(0, 20).map((b, i) => (
                  <tr key={i}>
                    <td>{String(b.id ?? b.type ?? i + 1)}</td>
                    <td className="fusion-mono fusion-text-micro">
                      {JSON.stringify(b).slice(0, 120)}…
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : !transfers.length ? (
            <p className="fusion-text-micro text-[var(--fusion-text-tertiary)] mt-2">
              Нет TRANSFER_*/COUNTERPARTY в графе — запустите Collect (onchain_explorer, depth≥2) и
              merge.
            </p>
          ) : null}
        </section>
      )
    }
    case 'osint-mentions': {
      const mentions = osintMentionNodes(bundle)
      const byId = new Map(nodes(bundle).map((n) => [n.id, n]))
      return (
        <section className="fusion-report-doc__section" id={`section-${sectionId}`}>
          <h2>OSINT Mentions</h2>
          {mentions.length ? (
            <div className="fusion-report-doc__table-wrap">
              <table className="fusion-report-doc__table">
                <thead>
                  <tr>
                    <th>Mention</th>
                    <th>Conf.</th>
                    <th>Linked from</th>
                  </tr>
                </thead>
                <tbody>
                  {mentions.slice(0, 40).map((m) => {
                    const linked = edges(bundle)
                      .filter((e) => e.target === m.id || e.source === m.id)
                      .map((e) => {
                        const other = e.source === m.id ? e.target : e.source
                        return shortEntityLabel(byId.get(other)?.label ?? other, 28)
                      })
                    return (
                      <tr key={m.id}>
                        <td>{shortEntityLabel(m.label ?? m.id, 48)}</td>
                        <td>{m.confidence != null ? `${Math.round(m.confidence * 100)}%` : '—'}</td>
                        <td className="fusion-text-micro">{linked.join(', ') || '—'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
              OSINT mentions не найдены в графе.
            </p>
          )}
        </section>
      )
    }
    case 'sanctions-exposure': {
      const flagged = flaggedWallets(bundle)
      const transfers = sanctionedTransferEdges(bundle)
      const byId = new Map(nodes(bundle).map((n) => [n.id, n]))
      return (
        <section className="fusion-report-doc__section" id={`section-${sectionId}`}>
          <h2>Санкции и Scam / Abuse</h2>
          <div className="fusion-report-doc__graph-stats">
            <div>
              <span className="stat fusion-tone-critical">{flagged.filter((w) => w.sanctioned).length}</span>
              <span className="label">SANCTIONED</span>
            </div>
            <div>
              <span className="stat fusion-tone-critical">{flagged.filter((w) => w.scam).length}</span>
              <span className="label">SCAM / ABUSE</span>
            </div>
            <div>
              <span className="stat">{transfers.length}</span>
              <span className="label">FLAGGED TRANSFERS</span>
            </div>
          </div>
          {flagged.length ? (
            <div className="fusion-report-doc__table-wrap mt-4">
              <table className="fusion-report-doc__table">
                <thead>
                  <tr>
                    <th>Wallet</th>
                    <th>Flags</th>
                    <th>Attribution</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody>
                  {flagged.slice(0, 40).map((w) => (
                    <tr key={w.id}>
                      <td className="fusion-mono">
                        {shortEntityLabel(w.address ?? w.label ?? w.id, 36)}
                      </td>
                      <td className="fusion-tone-critical">
                        {[w.sanctioned ? 'SANCTIONS' : null, w.scam ? 'SCAM' : null]
                          .filter(Boolean)
                          .join(' · ') || (w.flags ?? []).join(' · ')}
                      </td>
                      <td>{w.attribution ?? w.owner ?? '—'}</td>
                      <td className="fusion-text-micro">
                        {(w.risk_tags ?? []).slice(0, 3).join(', ') || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="fusion-text-micro text-[var(--fusion-text-tertiary)] mt-2">
              Совпадений с OFAC / OpenSanctions / Chainabuse по seed и контрагентам не найдено.
            </p>
          )}
          {transfers.length ? (
            <div className="fusion-report-doc__table-wrap mt-4">
              <h3 className="fusion-text-micro uppercase text-[var(--fusion-text-tertiary)] mb-2">
                Переводы на flagged-кошельки
              </h3>
              <table className="fusion-report-doc__table">
                <thead>
                  <tr>
                    <th>From</th>
                    <th>Type</th>
                    <th>To</th>
                  </tr>
                </thead>
                <tbody>
                  {transfers.slice(0, 30).map((e) => (
                    <tr key={e.id}>
                      <td>{shortEntityLabel(byId.get(e.source)?.label ?? e.source, 28)}</td>
                      <td className="fusion-mono fusion-tone-critical">{e.rel_type}</td>
                      <td>{shortEntityLabel(byId.get(e.target)?.label ?? e.target, 28)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </section>
      )
    }
    case 'attribution-ownership': {
      const owners = attributedWallets(bundle)
      const platforms = nodes(bundle).filter((n) => {
        const k = (n.kind ?? '').toLowerCase()
        return k === 'platform' || k === 'subject' || k === 'registry_label'
      })
      return (
        <section className="fusion-report-doc__section" id={`section-${sectionId}`}>
          <h2>Атрибуция · биржа / организация / субъект</h2>
          {owners.length ? (
            <div className="fusion-report-doc__table-wrap">
              <table className="fusion-report-doc__table">
                <thead>
                  <tr>
                    <th>Wallet</th>
                    <th>Owner / Tag</th>
                    <th>Category</th>
                    <th>Conf.</th>
                  </tr>
                </thead>
                <tbody>
                  {owners.slice(0, 40).map((w) => (
                    <tr key={w.id}>
                      <td className="fusion-mono">
                        {shortEntityLabel(w.address ?? w.label ?? w.id, 32)}
                      </td>
                      <td>{w.attribution ?? w.owner ?? '—'}</td>
                      <td>{w.owner_category ?? '—'}</td>
                      <td>{w.confidence != null ? `${Math.round(w.confidence * 100)}%` : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
              Атрибуция не найдена — локальные CEX seeds / TronScan / VASP не совпали с адресами.
            </p>
          )}
          {platforms.length ? (
            <div className="fusion-report-doc__table-wrap mt-4">
              <h3 className="fusion-text-micro uppercase text-[var(--fusion-text-tertiary)] mb-2">
                Связанные сущности
              </h3>
              <table className="fusion-report-doc__table">
                <thead>
                  <tr>
                    <th>Kind</th>
                    <th>Label</th>
                    <th>Conf.</th>
                  </tr>
                </thead>
                <tbody>
                  {platforms.slice(0, 30).map((n) => (
                    <tr key={n.id}>
                      <td>{n.kind}</td>
                      <td>{n.label ?? n.id}</td>
                      <td>{n.confidence != null ? `${Math.round(n.confidence * 100)}%` : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </section>
      )
    }
    case 'risk': {
      const risk = deriveReportRisk(bundle)
      return (
        <section className="fusion-report-doc__section" id={`section-${sectionId}`}>
          <h2>Risk Assessment</h2>
          <div className="fusion-report-doc__risk-grid">
            <div>
              <span className="stat fusion-tone-critical">{risk.score}%</span>
              <span className="label">RISK SCORE</span>
            </div>
            <div>
              <span className="stat">{risk.level}</span>
              <span className="label">LEVEL</span>
            </div>
          </div>
          <ReportRiskHeatmap bundle={bundle} />
          <table className="fusion-report-doc__table mt-4">
            <thead>
              <tr>
                <th>Factor</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              {risk.factors.map((f) => (
                <tr key={f.label}>
                  <td>{f.label}</td>
                  <td>{f.value}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {bundle.riskHistory.points.length ? (
            <table className="fusion-report-doc__table mt-4">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Score</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {bundle.riskHistory.points.slice(-10).map((p) => (
                  <tr key={p.ts}>
                    <td>{fmtDate(p.ts)}</td>
                    <td>{p.score}</td>
                    <td>{p.source ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
        </section>
      )
    }
    case 'compliance-checklist':
      return (
        <section className="fusion-report-doc__section" id={`section-${sectionId}`}>
          <h2>Compliance Checklist</h2>
          <ul className="fusion-report-doc__checklist">
            <li className={bundle.readiness.fusion ? 'ok' : 'pending'}>
              OSINT Fusion completed
            </li>
            <li className={bundle.readiness.evidence ? 'ok' : 'pending'}>
              Evidence chain documented
            </li>
            <li className={bundle.readiness.generatedReports ? 'ok' : 'pending'}>
              115-ФЗ report generated
            </li>
            <li className={bundle.readiness.graph ? 'ok' : 'pending'}>
              Graph persisted
            </li>
          </ul>
        </section>
      )
    case 'recommendations': {
      const recs = (fusion?.recommended_actions_ru as string[] | undefined) ?? []
      return (
        <section className="fusion-report-doc__section" id={`section-${sectionId}`}>
          <h2>Recommendations</h2>
          {recs.length ? (
            <ul className="fusion-report-doc__list">
              {recs.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          ) : (
            <p className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
              {String(fusion?.decision_ru ?? 'Awaiting fusion recommendations.')}
            </p>
          )}
        </section>
      )
    }
    case 'analyst-notes':
      return (
        <section className="fusion-report-doc__section" id={`section-${sectionId}`}>
          <h2>Analyst Notes</h2>
          <p className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
            Use Investigation → Collaboration comments for operational notes.
          </p>
        </section>
      )
    case 'chain-of-custody':
      return (
        <section className="fusion-report-doc__section" id={`section-${sectionId}`}>
          <h2>Chain of Custody</h2>
          <p className="fusion-text-micro">
            ECCF-registered evidence with content hashes listed in Evidence section. Full audit via
            platform ECCF audit API per evidence item.
          </p>
        </section>
      )
    case 'appendices':
      return (
        <section className="fusion-report-doc__section" id={`section-${sectionId}`}>
          <h2>Appendices</h2>
          <p className="fusion-text-micro">
            Export raw graph JSON, evidence bundle, and regulator XML from Export Center.
          </p>
        </section>
      )
    case 'signature':
      return (
        <section className="fusion-report-doc__section fusion-report-doc__signature" id={`section-${sectionId}`}>
          <h2>Digital Signature</h2>
          <p className="fusion-mono fusion-text-micro text-[var(--fusion-text-tertiary)]">
            FinSkalp Reporting OS · {bundle.caseRef} · {new Date().toISOString()}
          </p>
        </section>
      )
    default:
      return null
  }
}

export function ReportToc({ sections }: { sections: ReportSectionId[] }) {
  const labels: Partial<Record<ReportSectionId, string>> = {
    'executive-summary': 'Executive Summary',
    'graph-snapshot': 'Graph',
    evidence: 'Evidence',
    timeline: 'Timeline',
    risk: 'Risk',
    'export-actions': 'Export',
  }
  return (
    <nav className="fusion-report-doc__toc" aria-label="Table of contents">
      {sections
        .filter((s) => s !== 'cover')
        .map((s) => (
          <a key={s} href={`#section-${s}`} className="fusion-report-doc__toc-link">
            {labels[s] ?? s.replace(/-/g, ' ')}
          </a>
        ))}
    </nav>
  )
}
