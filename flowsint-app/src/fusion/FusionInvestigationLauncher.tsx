import { useMemo, useState, type KeyboardEvent } from 'react'
import { toast } from 'sonner'

import { cn } from '@/lib/utils'

import { FusionCollectorPicker } from './FusionCollectorPicker'
import { FusionChainPicker } from './FusionChainPicker'
import { loadEnabledCollectors } from './fusion-collector-prefs'
import type { StartInvestigationParams } from './fusion-investigation-start'
import {
  parseSeedPool,
  personToUsernames,
  type InvestigationSeedItem,
  type SeedType,
} from './fusion-investigation-seed'
import { fusionCopy } from './fusion-copy'
import {
  inferWalletChain,
  isLikelyWalletAddress,
  resolveChainsToScan,
  type ChainMode,
} from './fusion-wallet-utils'

type TabId = 'wallet' | 'person' | 'organization' | 'pool'

type Props = {
  className?: string
  onSubmit: (params: StartInvestigationParams) => void
  isSubmitting?: boolean
}

const TABS: Array<{ id: TabId; label: string }> = [
  { id: 'wallet', label: 'Кошелёк' },
  { id: 'person', label: 'ФИО / person' },
  { id: 'organization', label: 'Организация' },
  { id: 'pool', label: 'Пул данных' },
]

function buildItems(
  tab: TabId,
  wallet: string,
  chainMode: ChainMode,
  personName: string,
  orgName: string,
  poolText: string
): InvestigationSeedItem[] {
  switch (tab) {
    case 'wallet': {
      const w = wallet.trim()
      if (!isLikelyWalletAddress(w)) throw new Error(fusionCopy.launcher.invalidWallet)
      const chains = resolveChainsToScan(w, chainMode)
      // Primary seed uses first chain; multi-chain scan flagged via chains[]
      return [
        {
          type: 'wallet',
          value: w,
          chain: chains[0] ?? inferWalletChain(w),
          chains,
          chainMode,
        },
      ]
    }
    case 'person': {
      const p = personName.trim()
      if (p.length < 2) throw new Error(fusionCopy.launcher.invalidPerson)
      return [{ type: 'person', value: p }]
    }
    case 'organization': {
      const o = orgName.trim()
      if (o.length < 2) throw new Error(fusionCopy.launcher.invalidOrg)
      return [{ type: 'organization', value: o }]
    }
    case 'pool': {
      const items = parseSeedPool(poolText)
      if (!items.length) throw new Error(fusionCopy.launcher.invalidPool)
      return items
    }
    default:
      return []
  }
}

export function FusionInvestigationLauncher({ className, onSubmit, isSubmitting = false }: Props) {
  const [tab, setTab] = useState<TabId>('wallet')
  const [wallet, setWallet] = useState('')
  const [chainMode, setChainMode] = useState<ChainMode>('auto')
  const [personName, setPersonName] = useState('')
  const [orgName, setOrgName] = useState('')
  const [poolText, setPoolText] = useState('')
  const [enabledCollectors, setEnabledCollectors] = useState<string[]>(() => loadEnabledCollectors())

  const previewUsernames = useMemo(
    () => (personName.trim() ? personToUsernames(personName) : []),
    [personName]
  )

  const validationHint = useMemo(() => {
    if (tab === 'wallet') {
      const w = wallet.trim()
      if (!w) return fusionCopy.launcher.walletHint
      if (!isLikelyWalletAddress(w)) return fusionCopy.launcher.walletInvalidHint
      return null
    }
    if (tab === 'person' && personName.trim().length < 2) return fusionCopy.launcher.personHint
    if (tab === 'organization' && orgName.trim().length < 2) return fusionCopy.launcher.orgHint
    if (tab === 'pool' && !parseSeedPool(poolText).length) return fusionCopy.launcher.poolHint
    return null
  }, [tab, wallet, personName, orgName, poolText])

  const launch = () => {
    try {
      const items = buildItems(tab, wallet, chainMode, personName, orgName, poolText)
      onSubmit({
        items,
        collectorIds: enabledCollectors.length ? enabledCollectors : undefined,
        depth: 2,
        combat: true,
      })
    } catch (err) {
      toast.error(err instanceof Error ? err.message : fusionCopy.launcher.launchFailed)
    }
  }

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !isSubmitting) {
      e.preventDefault()
      launch()
    }
  }

  return (
    <section
      className={cn(
        'fusion-surface-deck border border-[var(--fusion-border)] p-3',
        className
      )}
      data-testid="fusion-investigation-launcher"
      onKeyDown={handleKeyDown}
    >
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="fusion-heading-panel text-[11px] normal-case">Новое расследование</span>
        <span className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
          не demo — реальные collectors + KYT
        </span>
      </div>

      <div className="mb-3 flex flex-wrap gap-1">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={cn(
              'px-2 py-0.5 fusion-text-micro rounded-sm border',
              tab === t.id
                ? 'border-[var(--fusion-ops-blue)] text-[var(--fusion-ops-blue)]'
                : 'border-[var(--fusion-border)] text-[var(--fusion-text-tertiary)]'
            )}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'wallet' ? (
        <div className="flex flex-wrap items-end gap-2">
          <div className="min-w-[220px] flex-1">
            <label className="fusion-text-micro text-[var(--fusion-text-tertiary)]">Адрес</label>
            <input
              className="mt-1 w-full rounded-sm border border-[var(--fusion-border)] bg-[var(--fusion-bg-deck)] px-2 py-1.5 fusion-mono fusion-text-data"
              placeholder="T… (34 символа) / 0x… / bc1…"
              value={wallet}
              autoFocus
              onChange={(e) => {
                setWallet(e.target.value)
                if (isLikelyWalletAddress(e.target.value) && chainMode === 'auto') {
                  /* auto keeps inference at submit time */
                }
              }}
              onKeyDown={handleKeyDown}
            />
          </div>
          <FusionChainPicker value={chainMode} onChange={setChainMode} />
        </div>
      ) : null}

      {tab === 'person' ? (
        <div>
          <label className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
            Фамилия или ФИО — пробелы можно (Maigret / clearnet / санкции)
          </label>
          <input
            className="mt-1 w-full rounded-sm border border-[var(--fusion-border)] bg-[var(--fusion-bg-deck)] px-2 py-1.5 fusion-text-data"
            placeholder="Иванов Алексей Петрович"
            value={personName}
            onChange={(e) => setPersonName(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          {previewUsernames.length ? (
            <p className="mt-1 fusion-text-micro text-[var(--fusion-text-tertiary)]">
              Maigret handles: {previewUsernames.join(', ')}
            </p>
          ) : null}
        </div>
      ) : null}

      {tab === 'organization' ? (
        <div>
          <label className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
            Организация / юрлицо
          </label>
          <input
            className="mt-1 w-full rounded-sm border border-[var(--fusion-border)] bg-[var(--fusion-bg-deck)] px-2 py-1.5 fusion-text-data"
            placeholder="ООО … / Company Ltd"
            value={orgName}
            onChange={(e) => setOrgName(e.target.value)}
            onKeyDown={handleKeyDown}
          />
        </div>
      ) : null}

      {tab === 'pool' ? (
        <div>
          <label className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
            Пул — по строке на объект
          </label>
          <textarea
            className="mt-1 min-h-[88px] w-full rounded-sm border border-[var(--fusion-border)] bg-[var(--fusion-bg-deck)] px-2 py-1.5 fusion-mono fusion-text-data text-[11px]"
            placeholder={`wallet:TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t\nperson:Иванов Алексей\norg:ООО Пример\nusername:myhandle`}
            value={poolText}
            onChange={(e) => setPoolText(e.target.value)}
            onKeyDown={handleKeyDown}
          />
        </div>
      ) : null}

      {validationHint ? (
        <p className="mt-2 fusion-text-micro text-[var(--fusion-ops-yellow)]">{validationHint}</p>
      ) : null}

      <div className="mt-3">
        <FusionCollectorPicker enabledIds={enabledCollectors} onChange={setEnabledCollectors} compact />
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button
          type="button"
          className="px-3 py-1.5 fusion-text-micro border border-[var(--fusion-ops-blue)] text-[var(--fusion-ops-blue)] rounded-[var(--fusion-radius-sm)] disabled:opacity-50"
          disabled={isSubmitting}
          onClick={launch}
        >
          {isSubmitting ? fusionCopy.launcher.preparing : fusionCopy.launcher.start}
        </button>
        <span className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
          {fusionCopy.launcher.enterHint}
        </span>
      </div>
    </section>
  )
}

export type { SeedType, InvestigationSeedItem }
