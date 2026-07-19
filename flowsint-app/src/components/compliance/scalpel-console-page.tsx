import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Activity, AlertTriangle, CheckCircle2, Clock, Settings2, Wrench } from 'lucide-react'

import { complianceService, type ScalpelCollector } from '@/api/compliance-service'
import { PageLayout } from '@/components/layout/page-layout'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'

const GROUP_LABELS: Record<string, string> = {
  'on-chain': 'On-chain',
  sanctions: 'Sanctions',
  osint: 'OSINT',
  darknet: 'Darknet',
  registries: 'Registries',
}

function statusBadge(status: ScalpelCollector['ui_status']) {
  if (status === 'live') {
    return (
      <Badge className="rounded-sm border border-emerald-700/30 bg-emerald-950/20 text-emerald-400">
        LIVE
      </Badge>
    )
  }
  if (status === 'needs_config') {
    return (
      <Badge className="rounded-sm border border-amber-700/30 bg-amber-950/20 text-amber-400">
        needs config
      </Badge>
    )
  }
  return (
    <Badge className="rounded-sm border border-[var(--fusion-border)] bg-[var(--fusion-bg-deck)] text-[var(--fusion-text-secondary)]">
      in development
    </Badge>
  )
}

function CollectorCard({
  collector,
  onSelect,
}: {
  collector: ScalpelCollector
  onSelect: (c: ScalpelCollector) => void
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(collector)}
      className="flex h-full flex-col rounded-md border border-[var(--fusion-border)] bg-[var(--fusion-bg-panel)] p-4 text-left shadow-sm transition-colors hover:border-[var(--fusion-ops-blue)]/40 hover:bg-[var(--fusion-bg-deck)]"
    >
      <div className="mb-2 flex items-start justify-between gap-2">
        <h3 className="text-sm font-semibold text-[var(--fusion-text-primary)]">{collector.name}</h3>
        {statusBadge(collector.ui_status)}
      </div>
      <p className="mb-4 flex-1 text-xs leading-relaxed text-[var(--fusion-text-secondary)]">
        {collector.description}
      </p>
      <div className="flex flex-wrap gap-2 text-[10px] text-[var(--fusion-text-tertiary)]">
        <span className="inline-flex items-center gap-1">
          <Activity className="h-3 w-3" />
          {collector.request_count} requests
        </span>
        {collector.last_health_check ? (
          <span className="inline-flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {new Date(collector.last_health_check).toLocaleString()}
          </span>
        ) : null}
        {collector.health_status === 'ok' ? (
          <CheckCircle2 className="h-3 w-3 text-emerald-500" />
        ) : collector.health_status ? (
          <AlertTriangle className="h-3 w-3 text-amber-500" />
        ) : null}
      </div>
    </button>
  )
}

function CollectorDetail({
  collector,
  open,
  onOpenChange,
}: {
  collector: ScalpelCollector | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  if (!collector) return null

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full overflow-y-auto border-l border-[var(--fusion-border)] bg-[var(--fusion-bg-interactive)] sm:max-w-xl">
        <SheetHeader>
          <div className="flex items-center gap-2">
            {statusBadge(collector.ui_status)}
            <SheetTitle>{collector.name}</SheetTitle>
          </div>
          <SheetDescription>{collector.description}</SheetDescription>
        </SheetHeader>

        <div className="mt-6 space-y-5 text-sm">
          <section className="rounded-md border border-[var(--fusion-border)] p-3">
            <div className="mb-2 font-medium">Health</div>
            <dl className="grid grid-cols-2 gap-2 text-xs text-[var(--fusion-text-secondary)]">
              <div>
                <dt>Status</dt>
                <dd className="font-mono text-[var(--fusion-text-primary)]">
                  {collector.health_status ?? 'unknown'}
                </dd>
              </div>
              <div>
                <dt>Latency</dt>
                <dd className="font-mono text-[var(--fusion-text-primary)]">
                  {collector.latency_ms != null ? `${collector.latency_ms} ms` : '—'}
                </dd>
              </div>
              <div>
                <dt>Requests</dt>
                <dd className="font-mono text-[var(--fusion-text-primary)]">{collector.request_count}</dd>
              </div>
              <div>
                <dt>Errors</dt>
                <dd className="font-mono text-[var(--fusion-text-primary)]">{collector.error_count}</dd>
              </div>
            </dl>
          </section>

          {collector.api_key_hint ? (
            <section className="rounded-md border border-[var(--fusion-border)] p-3">
              <div className="mb-2 flex items-center gap-2 font-medium">
                <Settings2 className="h-4 w-4" />
                API key settings
              </div>
              <p className="text-xs text-[var(--fusion-text-secondary)]">{collector.api_key_hint}</p>
              {collector.requires_env?.length ? (
                <p className="mt-2 font-mono text-[10px] text-[var(--fusion-text-tertiary)]">
                  Env: {collector.requires_env.join(', ')}
                </p>
              ) : null}
            </section>
          ) : null}

          <section className="rounded-md border border-[var(--fusion-border)] p-3">
            <div className="mb-2 font-medium">Call history</div>
            {collector.call_history?.length ? (
              <ul className="space-y-2 text-xs text-[var(--fusion-text-secondary)]">
                {collector.call_history.map((row) => (
                  <li key={row.id} className="rounded border border-[var(--fusion-border)] p-2">
                    <div className="font-mono text-[10px]">{row.type}</div>
                    <div>{row.text_ru || '—'}</div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-[var(--fusion-text-tertiary)]">No recent calls recorded.</p>
            )}
          </section>

          <section className="rounded-md border border-[var(--fusion-border)] p-3">
            <div className="mb-2 font-medium">Recent errors</div>
            {collector.recent_errors?.length ? (
              <ul className="space-y-2 text-xs text-amber-400">
                {collector.recent_errors.map((row) => (
                  <li key={`err-${row.id}`}>{row.text_ru || row.type}</li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-[var(--fusion-text-tertiary)]">No recent errors.</p>
            )}
          </section>
        </div>
      </SheetContent>
    </Sheet>
  )
}

export function ScalpelConsolePage({ embedded = false }: { embedded?: boolean }) {
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<ScalpelCollector | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)

  const catalogQuery = useQuery({
    queryKey: ['compliance', 'scalpel-collectors'],
    queryFn: () => complianceService.getScalpelCollectors(),
    refetchInterval: 60_000,
  })

  const filteredGroups = useMemo(() => {
    const groups = catalogQuery.data?.groups ?? {}
    const order = catalogQuery.data?.group_order ?? Object.keys(groups)
    const q = search.trim().toLowerCase()
    const out: Array<[string, ScalpelCollector[]]> = []
    for (const key of order) {
      const items = (groups[key] ?? []).filter(
        (c) =>
          !q ||
          c.name.toLowerCase().includes(q) ||
          c.description.toLowerCase().includes(q) ||
          c.id.toLowerCase().includes(q)
      )
      if (items.length) out.push([key, items])
    }
    return out
  }, [catalogQuery.data, search])

  const summary = catalogQuery.data?.health_summary

  const body = (
      <div className="space-y-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline" className="gap-1">
              <Wrench className="h-3 w-3" />
              {catalogQuery.data?.collectors?.length ?? '…'} collectors
            </Badge>
            {summary ? (
              <>
                <Badge variant="outline">
                  health: {summary.status ?? 'unknown'} ({summary.collectors_ok ?? 0}/
                  {summary.collectors_total ?? 0})
                </Badge>
                {summary.checked_at ? (
                  <Badge variant="outline" className="font-mono text-[10px]">
                    checked {new Date(summary.checked_at).toLocaleString()}
                  </Badge>
                ) : null}
              </>
            ) : null}
          </div>
          <div className="w-full md:max-w-sm">
            <Input
              placeholder="Search collectors…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        {catalogQuery.isLoading ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-36 rounded-md" />
            ))}
          </div>
        ) : catalogQuery.isError ? (
          <div className="rounded-md border border-dashed p-6 text-sm text-[var(--fusion-text-secondary)]">
            Collector catalog unavailable. Ensure compliance API exposes{' '}
            <code className="font-mono text-xs">/api/compliance/scalpel/collectors</code>.
          </div>
        ) : (
          filteredGroups.map(([groupKey, items]) => (
            <section key={groupKey} className="space-y-3">
              <h2 className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--fusion-text-tertiary)]">
                {GROUP_LABELS[groupKey] ?? groupKey}
              </h2>
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {items.map((collector) => (
                  <CollectorCard
                    key={collector.id}
                    collector={collector}
                    onSelect={(c) => {
                      setSelected(c)
                      setDetailOpen(true)
                    }}
                  />
                ))}
              </div>
            </section>
          ))
        )}

        <CollectorDetail collector={selected} open={detailOpen} onOpenChange={setDetailOpen} />

        <div className="flex justify-end">
          <Button
            size="sm"
            variant="outline"
            disabled={catalogQuery.isFetching}
            onClick={() => catalogQuery.refetch()}
          >
            Refresh catalog
          </Button>
        </div>
      </div>
  )

  if (embedded) return body

  return (
    <PageLayout
      title="Scalpel Console"
      description="Operational catalog of Scalpel collectors — same sources as investigation OSINT checkboxes."
    >
      {body}
    </PageLayout>
  )
}
