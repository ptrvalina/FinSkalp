import { cn } from '@/lib/utils'

import { CHAIN_OPTIONS, type ChainMode } from './fusion-wallet-utils'

type Props = {
  value: ChainMode
  onChange: (mode: ChainMode) => void
  className?: string
  /** Compact button row (default) vs select */
  variant?: 'buttons' | 'select'
}

/** Blockchain picker with Auto + All networks combat modes. */
export function FusionChainPicker({ value, onChange, className, variant = 'buttons' }: Props) {
  if (variant === 'select') {
    return (
      <select
        className={cn(
          'rounded-sm border border-[var(--fusion-border)] bg-[var(--fusion-bg-deck)] px-2 py-1.5 fusion-text-micro',
          className
        )}
        value={value}
        onChange={(e) => onChange(e.target.value as ChainMode)}
        data-testid="fusion-chain-picker"
        aria-label="Сеть блокчейна"
      >
        {CHAIN_OPTIONS.map((o) => (
          <option key={o.id} value={o.id}>
            {o.label}
          </option>
        ))}
      </select>
    )
  }

  return (
    <div
      className={cn('flex flex-wrap items-center gap-1', className)}
      data-testid="fusion-chain-picker"
      role="group"
      aria-label="Сеть блокчейна"
    >
      <span className="fusion-text-micro text-[var(--fusion-text-tertiary)] mr-1">Сеть</span>
      {CHAIN_OPTIONS.map((o) => {
        const isCombat = o.id === 'auto' || o.id === 'all'
        const active = value === o.id
        return (
          <button
            key={o.id}
            type="button"
            title={o.hint}
            className={cn(
              'px-2 py-1 fusion-text-micro rounded-sm border',
              active && isCombat && 'border-[var(--fusion-ops-green)] text-[var(--fusion-ops-green)] bg-[color-mix(in_srgb,var(--fusion-ops-green)_12%,transparent)]',
              active && !isCombat && 'border-[var(--fusion-ops-blue)] text-[var(--fusion-ops-blue)]',
              !active && 'border-[var(--fusion-border)] text-[var(--fusion-text-tertiary)]'
            )}
            onClick={() => onChange(o.id)}
          >
            {o.label}
          </button>
        )
      })}
    </div>
  )
}
