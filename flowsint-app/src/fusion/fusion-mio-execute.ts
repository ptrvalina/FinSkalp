import {
  requestCenterGraph,
  requestGraphNodeFocus,
  setActiveDockTab,
  setGraphSearchOpen,
  setPanelFocus,
} from './fusion-sync-bus'
import type { MioExecutableCard } from './fusion-mio-actions'
import { toApiWorkflowStatus } from './fusion-mio-actions'
import { recordCaseAction } from './fusion-case-session'
import { complianceService } from '@/api/compliance-service'
import {
  filterCollectorsForSeed,
  defaultCollectorsForSeed,
  primaryWallet,
  resolveChain,
  scalpelTargetAddress,
  seedUsernames,
  type InvestigationSeedItem,
} from './fusion-investigation-seed'

export type MioExecuteDeps = {
  caseId: string
  caseRef?: string | null
  defaultWallet?: { address: string; chain?: string } | null
  investigationWallet?: { address: string; chain?: string } | null
  investigationSeedItems?: InvestigationSeedItem[]
  enabledCollectors?: string[]
  graphNodes?: Array<{ id: string; kind?: string; label?: string }> | null
  fuseMutation: { mutateAsync: () => Promise<unknown> }
  transitionMutation: { mutateAsync: (status: string) => Promise<unknown> }
  screenMutation: {
    mutateAsync: (payload: { address: string; chain?: string }) => Promise<unknown>
  }
  invalidateGraph?: () => void
  openReport?: (caseId: string) => void
}

function resolveSeedItems(deps: MioExecuteDeps): InvestigationSeedItem[] {
  if (deps.investigationSeedItems?.length) return deps.investigationSeedItems
  if (deps.investigationWallet) {
    return [
      {
        type: 'wallet',
        value: deps.investigationWallet.address,
        chain: deps.investigationWallet.chain,
      },
    ]
  }
  if (deps.defaultWallet) {
    return [{ type: 'wallet', value: deps.defaultWallet.address, chain: deps.defaultWallet.chain }]
  }
  return []
}

function resolveSeedWallet(deps: MioExecuteDeps) {
  const items = resolveSeedItems(deps)
  const w = primaryWallet(items)
  if (w) return { address: w.value, chain: w.chain }
  return deps.investigationWallet ?? deps.defaultWallet ?? null
}

export async function executeMioCardAction(
  card: MioExecutableCard,
  deps: MioExecuteDeps
): Promise<void> {
  const seedItems = resolveSeedItems(deps)
  const seedWallet = resolveSeedWallet(deps)

  switch (card.actionKind) {
    case 'fuse':
      await deps.fuseMutation.mutateAsync()
      break
    case 'run_scalpel': {
      if (!seedItems.length) {
        throw new Error('Укажите seed — панель «Новое расследование» или SEED в деле')
      }
      const collectors = filterCollectorsForSeed(
        deps.enabledCollectors?.length
          ? deps.enabledCollectors
          : defaultCollectorsForSeed(seedItems),
        seedItems
      )
      if (!collectors.length) {
        throw new Error('Нет доступных collectors для этого seed')
      }
      const chain = resolveChain(seedItems)
      const usernames = seedUsernames(seedItems)
      const result = await complianceService.scalpelCollect({
        address: scalpelTargetAddress(seedItems),
        chain,
        depth: 2,
        collectors,
        usernames: usernames.length ? usernames : undefined,
        caseRef: deps.caseRef ?? undefined,
      })
      if (result.evidence_graph) {
        await complianceService.mergeCaseGraph(deps.caseId, result.evidence_graph, 'append')
      }
      if (deps.caseRef) recordCaseAction(deps.caseRef, 'run_scalpel')
      deps.invalidateGraph?.()
      break
    }
    case 'transition': {
      const apiStatus = toApiWorkflowStatus(card.targetStatus)
      if (!apiStatus) throw new Error('Нет целевого статуса workflow')
      await deps.transitionMutation.mutateAsync(apiStatus)
      break
    }
    case 'screen_wallet': {
      let address = card.walletAddress ?? seedWallet?.address
      let chain = card.walletChain ?? seedWallet?.chain
      if (!address || address.startsWith('person:') || address.startsWith('org:'))
        throw new Error('KYT доступен только при seed-кошельке')
      const prefixed = address.match(/^(tron|eth|btc|bsc):(.+)$/i)
      if (prefixed) {
        chain = chain ?? prefixed[1]!.toLowerCase()
        address = prefixed[2]!
      }
      if (address.startsWith('wallet:')) {
        const rest = address.slice('wallet:'.length)
        const m2 = rest.match(/^(tron|eth|btc|bsc):(.+)$/i)
        if (m2) {
          chain = chain ?? m2[1]!.toLowerCase()
          address = m2[2]!
        } else {
          address = rest
        }
      }
      await deps.screenMutation.mutateAsync({
        address,
        chain,
      })
      if (deps.caseRef) recordCaseAction(deps.caseRef, 'screen_wallet')
      break
    }
    case 'open_report':
      if (deps.openReport) {
        deps.openReport(deps.caseId)
        break
      }
      throw new Error('Открытие отчёта недоступно')
    case 'open_evidence':
      setActiveDockTab('evidence')
      setPanelFocus('evidence')
      break
    case 'refresh_graph':
      deps.invalidateGraph?.()
      requestCenterGraph()
      break
    case 'focus_seed': {
      setGraphSearchOpen(true)
      setPanelFocus('graph-layers')
      const wallet = deps.graphNodes?.find((n) => {
        const kind = (n.kind ?? '').toLowerCase()
        return kind.includes('wallet') || kind.includes('address')
      })
      const subject = deps.graphNodes?.find((n) => (n.kind ?? '').toLowerCase() === 'subject')
      const focus = wallet ?? subject
      if (focus) requestGraphNodeFocus(focus.id)
      else requestCenterGraph()
      break
    }
    default:
      throw new Error('Действие не сопоставлено — см. текст рекомендации')
  }
}
