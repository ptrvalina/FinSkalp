import { useState } from 'react'

import { toast } from 'sonner'

import { cn } from '@/lib/utils'

import { FusionCollectorPicker } from './FusionCollectorPicker'
import { FusionChainPicker } from './FusionChainPicker'
import { loadCaseSession, mergeCaseSession } from './fusion-case-session'
import { loadEnabledCollectors } from './fusion-collector-prefs'
import { fusionCopy } from './fusion-copy'
import { parseSeedPool, type InvestigationSeedItem } from './fusion-investigation-seed'
import { isLikelyWalletAddress, resolveChainsToScan, type ChainMode } from './fusion-wallet-utils'

type Props = {
  caseRef: string
  className?: string
  onUpdated?: () => void
  /** Queue mid-case pipeline after save. */
  onRunPipeline?: () => void
}

function formatSeedSummary(items: InvestigationSeedItem[]): string {
  if (!items.length) return '—'
  return items
    .slice(0, 3)
    .map((i) => `${i.type}:${i.value.slice(0, 16)}${i.value.length > 16 ? '…' : ''}`)
    .join(' · ')
}

export function FusionCaseSeedBar({ caseRef, className, onUpdated, onRunPipeline }: Props) {
  const session = loadCaseSession(caseRef)
  const seedItems = session.investigationSeed?.items ?? []
  const walletFromSeed = seedItems.find((i) => i.type === 'wallet')
  const legacyWallet = session.investigationWallet

  const [poolText, setPoolText] = useState(
    seedItems.length
      ? seedItems.map((i) => `${i.type}:${i.value}`).join('\n')
      : legacyWallet
        ? `wallet:${legacyWallet.address}`
        : ''
  )
  const [chainMode, setChainMode] = useState<ChainMode>(
    (walletFromSeed?.chainMode as ChainMode) ||
      (walletFromSeed?.chain as ChainMode) ||
      (legacyWallet?.chain as ChainMode) ||
      'auto'
  )
  const [enabledCollectors, setEnabledCollectors] = useState<string[]>(
    session.enabledCollectors?.length ? session.enabledCollectors : loadEnabledCollectors()
  )
  const [expanded, setExpanded] = useState(seedItems.length === 0 && !legacyWallet)

  const persist = (runPipeline: boolean) => {
    const items = parseSeedPool(poolText)
    if (!items.length && legacyWallet) {
      items.push({
        type: 'wallet',
        value: legacyWallet.address,
        chain: legacyWallet.chain,
      })
    }
    if (!items.length) return

    const wallet = items.find((i) => i.type === 'wallet')
    if (wallet) {
      const chains = resolveChainsToScan(wallet.value, chainMode)
      wallet.chain = chains[0]
      wallet.chains = chains
      wallet.chainMode = chainMode
    }
    mergeCaseSession(caseRef, {
      investigationSeed: { items },
      investigationWallet: wallet
        ? { address: wallet.value, chain: wallet.chain }
        : undefined,
      enabledCollectors,
      lastAction: runPipeline ? 'seed_and_run_pipeline' : 'set_seed_pool',
      lastActionAt: Date.now(),
      ...(runPipeline
        ? {
            pipelineStatus: 'pending' as const,
            pipelinePhase: 'collectors' as const,
            pipelineError: undefined,
          }
        : {}),
    })
    onUpdated?.()
    if (runPipeline) {
      onRunPipeline?.()
      toast.success(fusionCopy.investigation.seedSavedRun)
    } else {
      toast.success(fusionCopy.investigation.seedSaved)
    }
    setExpanded(false)
  }

  const displayItems =
    seedItems.length > 0
      ? seedItems
      : legacyWallet
        ? [{ type: 'wallet' as const, value: legacyWallet.address, chain: legacyWallet.chain }]
        : []

  return (
    <div
      className={cn(
        'border-b border-[var(--fusion-border)] bg-[var(--fusion-bg-panel)] px-3 py-2',
        className
      )}
      data-testid="fusion-case-seed-bar"
    >
      {displayItems.length > 0 && !expanded ? (
        <div className="flex flex-wrap items-center gap-2">
          <span className="fusion-text-micro text-[var(--fusion-text-tertiary)]">SEED</span>
          <span className="fusion-text-micro text-[var(--fusion-ops-cyan)] fusion-truncate max-w-[420px]">
            {formatSeedSummary(displayItems)}
          </span>
          <span className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
            · {enabledCollectors.length} tools
          </span>
          {onRunPipeline ? (
            <button
              type="button"
              className="fusion-text-micro text-[var(--fusion-ops-blue)]"
              onClick={() => {
                mergeCaseSession(caseRef, {
                  pipelineStatus: 'pending',
                  pipelinePhase: 'collectors',
                  pipelineError: undefined,
                  lastAction: 'rerun_pipeline',
                  lastActionAt: Date.now(),
                })
                onUpdated?.()
                onRunPipeline()
                toast.success(fusionCopy.investigation.seedSavedRun)
              }}
            >
              {fusionCopy.investigation.runCollectors}
            </button>
          ) : null}
          <button
            type="button"
            className="ml-auto fusion-text-micro text-[var(--fusion-ops-blue)]"
            onClick={() => setExpanded(true)}
          >
            изменить
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          <label className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
            Объекты расследования (wallet / person / org / username)
          </label>
          <textarea
            className="min-h-[72px] w-full rounded-sm border border-[var(--fusion-border)] bg-[var(--fusion-bg-deck)] px-2 py-1 fusion-mono fusion-text-data text-[11px]"
            value={poolText}
            onChange={(e) => setPoolText(e.target.value)}
            placeholder="wallet:T…&#10;person:Иванов&#10;org:ООО …"
          />
          {isLikelyWalletAddress(poolText.split('\n')[0]?.replace(/^wallet:/i, '').trim() ?? '') ? (
            <FusionChainPicker value={chainMode} onChange={setChainMode} />
          ) : null}
          <FusionCollectorPicker
            enabledIds={enabledCollectors}
            onChange={(ids) => {
              setEnabledCollectors(ids)
              mergeCaseSession(caseRef, { enabledCollectors: ids })
            }}
            compact
          />
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="px-2 py-1 fusion-text-micro border border-[var(--fusion-border)] rounded-sm"
              onClick={() => persist(false)}
            >
              Сохранить seed + tools
            </button>
            <button
              type="button"
              className="px-2 py-1 fusion-text-micro border border-[var(--fusion-ops-blue)] text-[var(--fusion-ops-blue)] rounded-sm"
              onClick={() => persist(true)}
            >
              {fusionCopy.investigation.runCollectors}
            </button>
            {displayItems.length ? (
              <button
                type="button"
                className="px-2 py-1 fusion-text-micro text-[var(--fusion-text-tertiary)]"
                onClick={() => setExpanded(false)}
              >
                отмена
              </button>
            ) : null}
          </div>
        </div>
      )}
    </div>
  )
}
