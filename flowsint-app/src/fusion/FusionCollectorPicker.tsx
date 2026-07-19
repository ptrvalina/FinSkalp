import { useEffect, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'

import { complianceService } from '@/api/compliance-service'
import { cn } from '@/lib/utils'

import {
  loadEnabledCollectors,
  mergeCollectorsWithCatalog,
  saveEnabledCollectors,
  toggleCollector,
} from './fusion-collector-prefs'

type Props = {
  enabledIds: string[]
  onChange: (ids: string[]) => void
  compact?: boolean
  className?: string
}

export function FusionCollectorPicker({ enabledIds, onChange, compact, className }: Props) {
  const catalogQuery = useQuery({
    queryKey: ['compliance', 'scalpel-collectors'],
    queryFn: () => complianceService.getScalpelCollectors(),
    staleTime: 60_000,
  })

  const collectors = catalogQuery.data?.collectors ?? []

  useEffect(() => {
    if (!collectors.length || enabledIds.length) return
    const stored = loadEnabledCollectors()
    const initial = mergeCollectorsWithCatalog(stored, collectors)
    if (initial.length) onChange(initial)
  }, [collectors, enabledIds.length, onChange])

  const grouped = useMemo(() => {
    const order = catalogQuery.data?.group_order ?? []
    const groups = catalogQuery.data?.groups ?? {}
    return order
      .map((key) => [key, groups[key] ?? []] as const)
      .filter(([, items]) => items.length > 0)
  }, [catalogQuery.data])

  const handleToggle = (id: string, checked: boolean) => {
    const next = toggleCollector(id, checked, enabledIds)
    onChange(next)
  }

  const selectAllSelectable = () => {
    const all = collectors.filter((c) => c.selectable !== false).map((c) => c.id)
    saveEnabledCollectors(all)
    onChange(all)
  }

  const clearAll = () => {
    saveEnabledCollectors([])
    onChange([])
  }

  if (catalogQuery.isLoading) {
    return <p className="fusion-text-micro text-[var(--fusion-text-tertiary)]">Загрузка инструментов…</p>
  }

  if (catalogQuery.isError) {
    return (
      <p className="fusion-text-micro fusion-tone-warning">
        Каталог collectors недоступен — проверьте API /scalpel/collectors
      </p>
    )
  }

  return (
    <div className={cn('space-y-2', className)} data-testid="fusion-collector-picker">
      <div className="flex flex-wrap items-center gap-2">
        <span className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
          Ручной режим · {enabledIds.length} вкл.
        </span>
        <button type="button" className="fusion-text-micro text-[var(--fusion-ops-blue)]" onClick={selectAllSelectable}>
          все
        </button>
        <button type="button" className="fusion-text-micro text-[var(--fusion-text-tertiary)]" onClick={clearAll}>
          снять
        </button>
      </div>
      {grouped.map(([groupKey, items]) => (
        <div key={groupKey}>
          {!compact ? (
            <div className="fusion-text-micro mb-1 uppercase text-[var(--fusion-text-tertiary)]">{groupKey}</div>
          ) : null}
          <div className={cn('flex flex-wrap gap-1', compact && 'gap-0.5')}>
            {items.map((collector) => {
              const disabled = collector.selectable === false
              const checked = !disabled && enabledIds.includes(collector.id)
              return (
                <label
                  key={collector.id}
                  className={cn(
                    'inline-flex cursor-pointer items-center gap-1 rounded-sm border px-1.5 py-0.5 fusion-text-micro',
                    disabled && 'cursor-not-allowed opacity-40',
                    checked
                      ? 'border-[var(--fusion-ops-blue)]/50 text-[var(--fusion-ops-blue)]'
                      : 'border-[var(--fusion-border)] text-[var(--fusion-text-secondary)]'
                  )}
                  title={collector.description}
                >
                  <input
                    type="checkbox"
                    className="h-3 w-3 accent-[var(--fusion-ops-blue)]"
                    disabled={disabled}
                    checked={checked}
                    onChange={(e) => handleToggle(collector.id, e.target.checked)}
                  />
                  <span className="fusion-truncate max-w-[140px]">{collector.name}</span>
                  {collector.ui_status === 'needs_config' ? (
                    <span className="text-[var(--fusion-ops-yellow)]">*</span>
                  ) : null}
                </label>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}
