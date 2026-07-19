import { complianceService } from '@/api/compliance-service'

import { loadCaseSession, mergeCaseSession } from './fusion-case-session'
import {
  buildCaseRefFromSeed,
  defaultCollectorsForSeed,
  filterCollectorsForSeed,
  primaryWallet,
  resolveChain,
  scalpelTargetAddress,
  seedUsernames,
  workflowSeedFromItems,
  type InvestigationSeed,
  type InvestigationSeedItem,
} from './fusion-investigation-seed'
import {
  resolveChainsToScan,
  type ChainMode,
  type WalletChain,
} from './fusion-wallet-utils'

export type StartInvestigationParams = {
  items: InvestigationSeedItem[]
  collectorIds?: string[]
  depth?: number
  /** When true (default), union seed defaults and enforce depth ≥ 2. */
  combat?: boolean
}

export type StartInvestigationResult = {
  caseRef: string
  caseId: string
  mentions: number
  graphNodes: number
  screened: boolean
}

export type PrepareInvestigationResult = {
  caseRef: string
  caseId: string
  depth: number
}

async function ensureCase(caseRef: string) {
  try {
    return await complianceService.createCase(caseRef)
  } catch {
    const inbox = await complianceService.listInbox()
    const row = inbox.find((r) => r.case_ref === caseRef)
    if (row?.case_id) return complianceService.getCase(row.case_id)
    const cases = await complianceService.listCases()
    const found = cases.find((c) => c.case_ref === caseRef)
    if (found) return found
    throw new Error(`Не удалось открыть дело ${caseRef}`)
  }
}

async function resolveCaseByRef(caseRef: string) {
  const inbox = await complianceService.listInbox()
  const row = inbox.find((r) => r.case_ref === caseRef)
  if (row?.case_id) return complianceService.getCase(row.case_id)
  const cases = await complianceService.listCases()
  const found = cases.find((c) => c.case_ref === caseRef)
  if (found) return found
  throw new Error(`Дело ${caseRef} не найдено`)
}

/** Union analyst prefs with seed-aware defaults; ensure wallet screening collectors. */
function resolveCollectorsForSeed(
  items: InvestigationSeedItem[],
  preferred?: string[],
  expandDefaults = true
): string[] {
  const raw = preferred?.length ? preferred : defaultCollectorsForSeed(items)
  let collectors = filterCollectorsForSeed(raw, items)
  if (expandDefaults) {
    for (const id of defaultCollectorsForSeed(items)) {
      if (!collectors.includes(id)) collectors = [...collectors, id]
    }
  }
  const wallet = primaryWallet(items)
  if (wallet && !collectors.includes('onchain_explorer')) {
    collectors = ['onchain_explorer', ...collectors]
  }
  if (wallet) {
    for (const id of ['sanctions_watchlist', 'abuse_scam_registry', 'vasp_registry'] as const) {
      if (!collectors.includes(id)) collectors = [...collectors, id]
    }
  }
  return collectors
}

/** Apply seed + collectors to an existing case ref (investigation workspace). */
export async function applySeedToCase(
  caseRef: string,
  params: StartInvestigationParams,
  options?: { runPipeline?: boolean }
): Promise<PrepareInvestigationResult> {
  const items = params.items.filter((i) => i.value.trim())
  if (!items.length) throw new Error('Укажите объект расследования')

  const caseRow = await ensureCase(caseRef)
  const chain = resolveChain(items)
  const wallet = primaryWallet(items)
  const collectors = resolveCollectorsForSeed(
    items,
    params.collectorIds,
    params.combat !== false
  )

  if (!collectors.length) {
    throw new Error('Выберите хотя бы один инструмент (collector)')
  }

  const runPipeline = options?.runPipeline !== false
  const depth = Math.max(params.depth ?? 2, params.combat !== false ? 2 : 1)
  const sessionPatch = {
    investigationSeed: { items } satisfies InvestigationSeed,
    enabledCollectors: collectors,
    lastAction: runPipeline ? 'start_investigation' : 'set_seed',
    lastActionAt: Date.now(),
    ...(runPipeline
      ? {
          pipelineStatus: 'pending' as const,
          pipelinePhase: 'collectors' as const,
          pipelineError: undefined,
        }
      : {}),
  }
  if (wallet) {
    mergeCaseSession(caseRef, {
      ...sessionPatch,
      investigationWallet: {
        address: wallet.value,
        chain: wallet.chain ?? chain,
      },
    })
  } else {
    mergeCaseSession(caseRef, sessionPatch)
  }

  const wf = workflowSeedFromItems(items)
  try {
    await complianceService.startWorkflowInvestigation({
      caseRef,
      seedType: wf.seed_type,
      seedValue: wf.seed_value,
      chain: wf.chain,
    })
  } catch {
    /* workflow workspace optional */
  }

  for (const item of items) {
    try {
      await complianceService.registerEccfEvidence({
        entityType: item.type,
        entityValue: item.value,
        caseRef,
        sourceType: 'analyst_seed',
        bridgeKg: true,
      })
    } catch {
      /* non-blocking */
    }
  }

  return {
    caseRef,
    caseId: caseRow.id,
    depth,
  }
}

/** Fast path: create case, seed session, register ECCF — no collectors yet. */
export async function prepareInvestigation(
  params: StartInvestigationParams
): Promise<PrepareInvestigationResult> {
  const items = params.items.filter((i) => i.value.trim())
  if (!items.length) throw new Error('Укажите объект расследования')

  const caseRef = buildCaseRefFromSeed(items)
  return applySeedToCase(caseRef, params)
}

/** Slow path: Scalpel collectors → graph merge → KYT. Runs on investigation workspace. */
export async function runInvestigationPipeline(
  caseRef: string,
  depth = 2
): Promise<StartInvestigationResult> {
  const session = loadCaseSession(caseRef)
  const items = session.investigationSeed?.items ?? []
  if (!items.length) {
    throw new Error('Нет seed-объектов для расследования')
  }

  const caseRow = await resolveCaseByRef(caseRef)
  const chain = resolveChain(items)
  const wallet = primaryWallet(items)
  const usernames = seedUsernames(items)
  const collectors = resolveCollectorsForSeed(items, session.enabledCollectors)

  if (!collectors.length) {
    throw new Error('Выберите хотя бы один collector')
  }

  const chainMode = (wallet?.chainMode ?? 'auto') as ChainMode
  const chainsToScan: WalletChain[] = wallet?.chains?.length
    ? (wallet.chains as WalletChain[])
    : wallet
      ? resolveChainsToScan(wallet.value, chainMode)
      : [chain as WalletChain]

  mergeCaseSession(caseRef, {
    pipelineStatus: 'running',
    pipelinePhase: 'collectors',
    pipelineError: undefined,
  })

  const address = scalpelTargetAddress(items)
  let graphNodes = 0
  let mentions = 0
  const sourceStatus: Record<string, string> = {}
  const collectorsRun: string[] = []
  const failedCollectors: string[] = []
  let firstCounterparties: string[] = []

  for (let i = 0; i < chainsToScan.length; i++) {
    const scanChain = chainsToScan[i]!
    const scalpel = await complianceService.scalpelCollect({
      address,
      chain: scanChain,
      depth: Math.max(depth, 2),
      collectors,
      usernames: usernames.length ? usernames : undefined,
      counterparties: firstCounterparties.length ? firstCounterparties : undefined,
      caseRef,
    })

    mentions += scalpel.mentions_count ?? 0
    const status =
      (scalpel.source_status as Record<string, string> | undefined) ??
      (scalpel.collector_status as Record<string, string> | undefined) ??
      {}
    for (const [k, v] of Object.entries(status)) {
      sourceStatus[`${scanChain}:${k}`] = String(v)
      if (String(v).toLowerCase().startsWith('error')) failedCollectors.push(`${scanChain}:${k}`)
    }
    if (Array.isArray(scalpel.collectors_run)) {
      collectorsRun.push(...(scalpel.collectors_run as string[]).map((c) => `${scanChain}:${c}`))
    }

    const entities = scalpel.extracted_entities as
      | { by_collector?: Record<string, { counterparties?: string[] }> }
      | undefined
    if (!firstCounterparties.length && entities?.by_collector) {
      for (const payload of Object.values(entities.by_collector)) {
        for (const cp of payload?.counterparties ?? []) {
          if (cp && !firstCounterparties.includes(cp)) firstCounterparties.push(cp)
        }
      }
      firstCounterparties = firstCounterparties.slice(0, 20)
    }

    const graphPayload = scalpel.evidence_graph
    if (graphPayload?.nodes?.length && caseRow.id) {
      const merged = await complianceService.mergeCaseGraph(
        caseRow.id,
        graphPayload,
        i === 0 ? 'replace' : 'append'
      )
      graphNodes = merged.graph_stats?.nodes ?? Math.max(graphNodes, graphPayload.nodes.length)
    }
  }

  mergeCaseSession(caseRef, {
    pipelinePhase: 'graph',
    pipelineCollectorStatus: sourceStatus,
    pipelineCollectorsRun: collectorsRun,
    pipelineError: failedCollectors.length
      ? `Collectors failed: ${failedCollectors.join(', ')}`
      : undefined,
  })

  if (!failedCollectors.length && mentions > 0 && !graphNodes) {
    throw new Error('Collectors вернули данные, но граф не построен — обновите API')
  }

  let screened = false
  if (wallet) {
    mergeCaseSession(caseRef, { pipelinePhase: 'kyt' })
    // KYT on primary inferred/selected chain
    const kytChain = chainsToScan[0] ?? wallet.chain ?? chain
    const kyt = await complianceService.screenWallet(wallet.value, kytChain)
    mergeCaseSession(caseRef, {
      lastKyt: {
        address: wallet.value,
        chain: kytChain,
        score: kyt.risk_score,
        level: kyt.risk_level,
        at: Date.now(),
      },
    })
    screened = true
  }

  mergeCaseSession(caseRef, {
    pipelineStatus: failedCollectors.length && !graphNodes ? 'error' : 'done',
    pipelinePhase: 'done',
    pipelineError: failedCollectors.length
      ? `Collectors failed: ${failedCollectors.join(', ')}`
      : undefined,
    lastAction: 'investigation_complete',
    lastActionAt: Date.now(),
  })

  return {
    caseRef,
    caseId: caseRow.id,
    mentions,
    graphNodes,
    screened,
  }
}

export function retryInvestigationPipeline(caseRef: string): void {
  mergeCaseSession(caseRef, {
    pipelineStatus: 'pending',
    pipelinePhase: 'collectors',
    pipelineError: undefined,
  })
}
