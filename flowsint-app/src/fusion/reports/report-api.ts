import { complianceService } from '@/api/compliance-service'
import { fetchWithAuth } from '@/api/api'
import { useAuthStore } from '@/stores/auth-store'

import {
  downloadJsonFile,
  downloadTextFile,
  graphNodesToCsv,
  graphToGraphMl,
} from './graph-export-utils'

const apiBase = () => import.meta.env.VITE_API_URL?.replace(/\/$/, '') ?? ''

export type ReportListItem = {
  case_id: string
  case_ref?: string
  report_id?: string
  typology_code?: string
  risk_level?: string
  decision_ru?: string
  generated_at?: string
}

export async function fetchReports(caseRef?: string): Promise<ReportListItem[]> {
  return complianceService.listReports(caseRef)
}

export function absoluteReportUrl(path: string): string {
  return `${apiBase()}${path}`
}

/** Download or preview a protected report export (PDF/HTML) with JWT. */
export async function openReportUrl(path: string): Promise<void> {
  // Prefer live Report Center module over empty regulator /report.pdf stub.
  if (path.includes('/report.pdf') && document.querySelector('.fusion-report-doc__body')) {
    const label =
      document.querySelector('.fusion-report-doc__toolbar h1')?.textContent?.trim() || 'Report Center'
    const caseRef =
      document.querySelector('.fusion-report-center [data-case-ref]')?.getAttribute('data-case-ref') ||
      window.location.pathname.split('/').filter(Boolean).at(-2) ||
      'case'
    printCurrentModulePdf(label, caseRef, { autoPrint: true })
    return
  }

  const blob = await fetchReportBlob(path)
  const textProbe = await blob.slice(0, 80).text()
  const looksHtml =
    blob.type.includes('html') ||
    /<!DOCTYPE\s+html/i.test(textProbe) ||
    /<html[\s>]/i.test(textProbe)

  // Backend often returns HTML under .pdf when WeasyPrint is missing.
  if (looksHtml || path.endsWith('.pdf')) {
    const html = looksHtml ? await blob.text() : null
    if (html) {
      // Regulator stub — still printable, but clearly not a module report.
      if (
        path.includes('/report.pdf') &&
        /Executive summary отсутствует|Индикаторы fusion не заполнены/i.test(html)
      ) {
        window.alert(
          'Регуляторный PDF пока пустой (нет fusion_result). Откройте модуль в Report Center и нажмите PDF / Print.'
        )
        return
      }
      printHtmlDocument(html, path.split('/').pop() ?? 'report')
      return
    }
  }

  const url = URL.createObjectURL(blob)
  window.open(url, '_blank')
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
}

/** Build printable HTML for the open Report Center module (not /report.pdf). */
function buildCurrentModulePrintHtml(moduleLabel: string, caseRef: string): string | null {
  const source =
    document.querySelector<HTMLElement>('.fusion-report-doc__body') ??
    document.querySelector<HTMLElement>('[data-testid="fusion-report-document"] article') ??
    document.querySelector<HTMLElement>('[data-testid="fusion-report-document"]')

  if (!source) return null

  const clone = source.cloneNode(true) as HTMLElement
  prepareCloneForPrint(clone)
  clone.querySelectorAll('.fusion-report-doc__toolbar, .fusion-report-doc__toc').forEach((el) => {
    el.remove()
  })

  const title = `${moduleLabel} — ${caseRef} — FinSkalp`
  return `<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${escapeHtml(title)}</title>
  <style>${REPORT_PRINT_CSS}</style>
</head>
<body>
  <header class="print-masthead">
    <div class="print-masthead__brand">FinSkalp · Financial Intelligence</div>
    <div class="print-masthead__meta">${escapeHtml(moduleLabel)} · ${escapeHtml(caseRef)}</div>
  </header>
  <main class="print-doc">${clone.innerHTML}</main>
</body>
</html>`
}

/** Print/PDF the open module as a standalone white document (avoids Dashboard shell). */
export function printCurrentModulePdf(
  moduleLabel: string,
  caseRef: string,
  options?: { autoPrint?: boolean }
): void {
  const html = buildCurrentModulePrintHtml(moduleLabel, caseRef)
  if (!html) {
    console.warn('[fusion] printCurrentModulePdf: report body not in DOM')
    window.alert('Тело отчёта не найдено на странице. Откройте модуль Report Center и повторите.')
    return
  }
  openStandaloneModuleDocument(html, { autoPrint: options?.autoPrint !== false })
}

export function openCurrentModulePdf(moduleLabel: string, caseRef: string): void {
  printCurrentModulePdf(moduleLabel, caseRef, { autoPrint: true })
}

function prepareCloneForPrint(root: HTMLElement): void {
  root.querySelectorAll('details').forEach((el) => {
    el.open = true
  })
  root
    .querySelectorAll<HTMLElement>(
      '.fusion-report-doc__sar-block, .fusion-report-doc__edge-details ul, .fusion-report-doc__table-wrap'
    )
    .forEach((el) => {
      el.style.maxHeight = 'none'
      el.style.overflow = 'visible'
      el.style.width = '100%'
    })
  root.querySelectorAll('button, [data-testid="fusion-report-pdf"], [data-testid="fusion-report-print"]').forEach((el) => {
    el.remove()
  })
}

/**
 * Open a standalone module HTML document and optionally print it.
 * Must run synchronously from a click handler (popup gesture).
 */
function openStandaloneModuleDocument(
  html: string,
  options: { autoPrint: boolean }
): void {
  // 1) about:blank + document.write — full control, correct print width
  const win = window.open('about:blank', '_blank')
  if (win) {
    try {
      win.document.open()
      win.document.write(html)
      win.document.close()
      const ok = (win.document.body?.innerHTML?.length ?? 0) > 80
      if (ok) {
        if (options.autoPrint) {
          window.setTimeout(() => {
            try {
              win.focus()
              win.print()
            } catch (err) {
              console.warn('[fusion] standalone print failed', err)
            }
          }, 400)
        }
        return
      }
      try {
        win.close()
      } catch {
        /* ignore */
      }
    } catch (err) {
      console.warn('[fusion] document.write failed', err)
      try {
        win.close()
      } catch {
        /* ignore */
      }
    }
  }

  // 2) In-page white sheet — reliable when popups are blocked / empty
  printViaInPageDocument(html)
}

/**
 * Inject printable markup into the page, hide chrome, print, tear down.
 * Fallback when popups are blocked.
 */
export function printViaInPageDocument(fullHtml: string): void {
  const styleMatch = fullHtml.match(/<style[^>]*>([\s\S]*?)<\/style>/i)
  const bodyMatch = fullHtml.match(/<body[^>]*>([\s\S]*?)<\/body>/i)
  const inner = bodyMatch?.[1] ?? fullHtml
  const styleText = styleMatch?.[1] ?? REPORT_PRINT_CSS

  document.getElementById('fusion-print-root')?.remove()
  document.getElementById('fusion-print-style')?.remove()

  const styleEl = document.createElement('style')
  styleEl.id = 'fusion-print-style'
  styleEl.textContent = `
${styleText}

body.fusion-print-mode > *:not(#fusion-print-root) {
  display: none !important;
}
body.fusion-print-mode {
  background: #fff !important;
  overflow: visible !important;
  height: auto !important;
  max-height: none !important;
  margin: 0 !important;
  padding: 0 !important;
}
#fusion-print-root {
  display: block !important;
  visibility: visible !important;
  position: static !important;
  z-index: 2147483646 !important;
  background: #fff !important;
  color: #111 !important;
  width: 100% !important;
  max-width: none !important;
  margin: 0 !important;
  padding: 12mm 10mm !important;
  box-sizing: border-box;
  overflow: visible !important;
}
@media print {
  html, body {
    background: #fff !important;
    overflow: visible !important;
    height: auto !important;
    margin: 0 !important;
    padding: 0 !important;
  }
  body.fusion-print-mode > *:not(#fusion-print-root) {
    display: none !important;
  }
  #fusion-print-root {
    padding: 0 !important;
  }
}
`
  document.head.appendChild(styleEl)

  const root = document.createElement('div')
  root.id = 'fusion-print-root'
  root.setAttribute('data-testid', 'fusion-print-root')
  root.innerHTML = inner
  document.body.appendChild(root)
  document.body.classList.add('fusion-print-mode')

  const cleanup = () => {
    document.body.classList.remove('fusion-print-mode')
    root.remove()
    styleEl.remove()
  }

  const after = () => {
    window.removeEventListener('afterprint', after)
    window.setTimeout(cleanup, 200)
  }
  window.addEventListener('afterprint', after)

  window.scrollTo(0, 0)
  void root.offsetHeight
  window.setTimeout(() => {
    try {
      window.print()
    } catch (err) {
      console.warn('[fusion] in-page print failed', err)
      cleanup()
    }
    window.setTimeout(() => {
      if (document.getElementById('fusion-print-root')) cleanup()
    }, 60_000)
  }, 300)
}

/** Open styled HTML in a standalone print tab. */
export function printHtmlDocument(html: string, title = 'FinSkalp report'): void {
  const payload =
    html.includes('@page') || html.includes('print-masthead')
      ? html
      : html.includes('<html')
        ? html.replace(/<\/head>/i, `<style>${REPORT_PRINT_CSS}</style></head>`)
        : `<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8"/><title>${escapeHtml(title)}</title><style>${REPORT_PRINT_CSS}</style></head><body><main class="print-doc">${html}</main></body></html>`
  openStandaloneModuleDocument(payload, { autoPrint: true })
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

/** Print stylesheet — avoid page-break-inside:avoid on tall sections (Chromium clips). */
const REPORT_PRINT_CSS = `
  @page { size: A4; margin: 12mm 10mm; }
  * { box-sizing: border-box; }
  html, body {
    margin: 0 !important;
    padding: 0 !important;
    width: 100% !important;
    height: auto !important;
    overflow: visible !important;
    background: #fff !important;
    color: #111 !important;
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.4;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
  .print-masthead {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    border-bottom: 1px solid #bbb;
    padding-bottom: 8px;
    margin-bottom: 14px;
    font-size: 9pt;
    color: #444;
  }
  .print-masthead__brand { font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase; }
  .print-doc {
    max-width: 100% !important;
    width: 100% !important;
    overflow: visible !important;
    margin: 0 !important;
    padding: 0 !important;
  }
  .print-doc *,
  .print-doc *::before,
  .print-doc *::after {
    max-width: 100% !important;
  }
  .print-doc section,
  .print-doc article,
  .print-doc table,
  .print-doc .fusion-report-doc__cover,
  .print-doc .fusion-report-doc__section,
  .print-doc .fusion-report-doc__findings {
    width: 100% !important;
    max-width: 100% !important;
    box-sizing: border-box !important;
  }
  h1, h2, h3 { color: #111; page-break-after: avoid; break-after: avoid; }
  h1 { font-size: 18pt; margin: 0 0 8px; }
  h2 { font-size: 10.5pt; text-transform: uppercase; letter-spacing: 0.08em; color: #333; margin: 16px 0 8px; border-bottom: 1px solid #ddd; padding-bottom: 4px; }
  h3 { font-size: 10pt; margin: 10px 0 6px; color: #444; }
  p, li, td, th, span, div { color: #111; }
  a { color: #111; text-decoration: none; }
  .fusion-report-doc__cover {
    text-align: center;
    padding: 10px 0 14px;
    margin-bottom: 14px;
    border-bottom: 1px solid #ccc;
    position: relative;
    page-break-after: avoid;
  }
  .fusion-report-doc__classification { font-size: 8pt; letter-spacing: 0.18em; color: #b00020; margin-bottom: 10px; }
  .fusion-report-doc__title { font-size: 20pt; font-weight: 600; margin: 0 0 6px; color: #111; }
  .fusion-report-doc__subtitle { font-size: 10pt; color: #555; margin: 0; }
  .fusion-report-doc__cover-meta { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 12px; text-align: left; }
  .fusion-report-doc__cover-meta .label { display: block; font-size: 8pt; color: #666; letter-spacing: 0.06em; }
  .fusion-report-doc__cover-meta .value { font-family: ui-monospace, Consolas, monospace; font-size: 9pt; }
  .fusion-report-doc__seal {
    position: absolute; right: 0; top: 0; width: 36px; height: 36px;
    border: 1px solid #999; display: flex; align-items: center; justify-content: center;
    font-size: 9pt; color: #333;
  }
  .fusion-report-doc__section {
    margin: 0 0 12px;
    padding: 0 0 8px;
    border-bottom: 1px solid #e5e5e5;
    overflow: visible !important;
    /* allow sections to split across pages */
    page-break-inside: auto;
    break-inside: auto;
  }
  .fusion-report-doc__findings {
    margin: 0 0 14px;
    padding: 10px 12px;
    border: 1px solid #ccc;
    background: #f7f7f7;
    page-break-inside: avoid;
  }
  .fusion-report-doc__findings-list { list-style: none; margin: 8px 0 0; padding: 0; }
  .fusion-report-doc__findings-list li { margin: 0 0 8px; padding-left: 10px; border-left: 3px solid #888; }
  .fusion-report-doc__findings-list li[data-tone="critical"] { border-left-color: #b00020; }
  .fusion-report-doc__findings-list li[data-tone="ops"] { border-left-color: #0a7ea4; }
  .fusion-report-doc__findings-list li strong {
    display: block; font-size: 8pt; text-transform: uppercase; letter-spacing: 0.06em; color: #555;
  }
  .fusion-report-doc__table {
    width: 100% !important;
    border-collapse: collapse;
    font-size: 8pt;
    margin: 6px 0;
    table-layout: auto;
  }
  .fusion-report-doc__table th,
  .fusion-report-doc__table td {
    border: 1px solid #ccc !important;
    padding: 4px 6px;
    text-align: left;
    vertical-align: top;
    color: #111 !important;
    background: #fff !important;
    word-break: break-word;
  }
  .fusion-report-doc__table th {
    background: #f0f0f0 !important;
    color: #333 !important;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-size: 7pt;
  }
  .fusion-report-doc__table-wrap,
  .fusion-report-doc__sar-block,
  .fusion-report-doc__edge-details ul {
    overflow: visible !important;
    max-height: none !important;
  }
  .fusion-report-doc__graph-stats { display: flex; flex-wrap: wrap; gap: 14px; margin: 8px 0 10px; }
  .fusion-report-doc__graph-stats .stat {
    display: block; font-size: 14pt; font-family: ui-monospace, Consolas, monospace; color: #111;
  }
  .fusion-report-doc__graph-stats .label {
    font-size: 7.5pt; color: #666; letter-spacing: 0.06em; text-transform: uppercase;
  }
  .fusion-report-doc__graph-viz {
    border: 1px solid #ccc; padding: 6px; margin: 6px 0; background: #fff;
    page-break-inside: avoid;
  }
  .fusion-report-doc__graph-viz svg { display: block; width: 100%; height: auto; max-height: 260px; }
  .fusion-report-doc__graph-legend {
    display: flex; flex-wrap: wrap; gap: 8px 14px; list-style: none;
    margin: 6px 0 0; padding: 0; font-size: 8pt; color: #444;
  }
  .fusion-report-doc__graph-legend .dot {
    display: inline-block; width: 8px; height: 8px; border-radius: 50%;
    margin-right: 4px; vertical-align: middle;
  }
  .fusion-report-doc__list,
  .fusion-report-doc__checklist,
  .fusion-report-doc__timeline { margin: 6px 0; padding-left: 18px; }
  .fusion-report-doc__checklist { list-style: none; padding-left: 0; }
  .fusion-report-doc__checklist li { padding: 4px 0; border-bottom: 1px solid #eee; font-size: 9pt; }
  .fusion-report-chart { margin: 8px 0; padding: 6px; border: 1px solid #ddd; page-break-inside: avoid; }
  .fusion-mono, .fusion-truncate { font-family: ui-monospace, Consolas, monospace; }
  .fusion-truncate { max-width: none !important; overflow: visible !important; text-overflow: clip !important; white-space: normal !important; }
  .fusion-tone-critical { color: #b00020 !important; }
  .fusion-text-micro, .fusion-text-section { color: #333 !important; }
  .max-w-\\[140px\\], .max-w-\\[200px\\], .max-w-\\[220px\\], .max-w-\\[160px\\] {
    max-width: none !important;
  }
  .mt-2, .mt-3, .mt-4 { margin-top: 10px; }
  .mb-2 { margin-bottom: 6px; }
  tr { page-break-inside: avoid; break-inside: avoid; }
`

/** Authenticated blob fetch for in-app PDF preview */
export async function fetchReportBlob(path: string): Promise<Blob> {
  const token = useAuthStore.getState().token
  const headers: HeadersInit = {}
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(`${apiBase()}${path}`, { headers })
  if (!res.ok) throw new Error(`Export failed: ${res.status}`)
  return res.blob()
}

export async function fetchReportJson(caseId: string): Promise<Record<string, unknown>> {
  return fetchWithAuth(complianceService.reportJsonUrl(caseId)) as Promise<Record<string, unknown>>
}

export async function exportKgEvidence(caseRef: string) {
  return complianceService.exportKgEvidence(caseRef)
}

export async function exportGraphJson(caseId: string, caseRef: string): Promise<void> {
  const graph = await complianceService.exportCaseGraph(caseId)
  downloadJsonFile(`${caseRef}-graph.json`, graph)
}

export async function exportGraphCsv(
  caseId: string,
  caseRef: string,
  graph?: { nodes: unknown[]; edges: unknown[] } | null
): Promise<void> {
  let nodes = (graph?.nodes ?? []) as Array<{
    id: string
    kind?: string
    label?: string
    confidence?: number
  }>
  if (!nodes.length) {
    const payload = await complianceService.exportCaseGraph(caseId)
    nodes = (payload.nodes ?? []) as typeof nodes
  }
  downloadTextFile(`${caseRef}-nodes.csv`, graphNodesToCsv(nodes), 'text/csv')
}

export async function exportGraphMl(
  caseId: string,
  caseRef: string,
  graph?: { nodes: unknown[]; edges: unknown[] } | null
): Promise<void> {
  let nodes = (graph?.nodes ?? []) as Array<{ id: string; kind?: string; label?: string }>
  let edges = (graph?.edges ?? []) as Array<{
    id?: string
    source: string
    target: string
    rel_type?: string
  }>
  if (!nodes.length) {
    const payload = await complianceService.exportCaseGraph(caseId)
    nodes = (payload.nodes ?? []) as typeof nodes
    edges = (payload.edges ?? []) as typeof edges
  }
  downloadTextFile(`${caseRef}.graphml`, graphToGraphMl({ nodes, edges }), 'application/xml')
}

export async function exportReportJson(caseId: string, caseRef: string): Promise<void> {
  const data = await fetchReportJson(caseId)
  downloadJsonFile(`${caseRef}-report.json`, data)
}

export async function exportCasePackage(
  caseId: string,
  caseRef: string,
  graph?: { nodes: unknown[]; edges: unknown[] } | null
): Promise<void> {
  const [report, evidence] = await Promise.all([
    fetchReportJson(caseId).catch(() => null),
    exportKgEvidence(caseRef).catch(() => null),
  ])
  downloadJsonFile(`${caseRef}-case-package.json`, {
    case_ref: caseRef,
    case_id: caseId,
    exported_at: new Date().toISOString(),
    report,
    evidence,
    graph: graph ?? null,
  })
}
