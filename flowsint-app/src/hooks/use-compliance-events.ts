import { useCallback, useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { complianceService, type OperatorEventCatalog } from '@/api/compliance-service'
import { connectSSE } from '@/api/sse'
import { useAuthStore } from '@/stores/auth-store'

const API_URL = import.meta.env.VITE_API_URL ?? ''

export type ComplianceLiveEvent = {
  id?: string
  type?: string
  severity?: string
  text_ru?: string
  ts?: number
  operator_event_type?: string
  platform_event_type?: string
  payload?: Record<string, unknown>
}

export function useComplianceEvents(options?: { enabled?: boolean; maxEvents?: number }) {
  const enabled = options?.enabled ?? true
  const maxEvents = options?.maxEvents ?? 50
  const token = useAuthStore((s) => s.token)
  const [liveEvents, setLiveEvents] = useState<ComplianceLiveEvent[]>([])

  const catalogQuery = useQuery({
    queryKey: ['compliance', 'operator-events-catalog'],
    queryFn: () => complianceService.getOperatorEventCatalog(),
    enabled,
    staleTime: 300_000,
  })

  useEffect(() => {
    if (!enabled || !token) return

    const dispose = connectSSE({
      url: `${API_URL}/api/compliance/events/stream`,
      onMessage: (raw) => {
        try {
          const parsed =
            typeof raw.data === 'string'
              ? (JSON.parse(raw.data) as ComplianceLiveEvent)
              : (raw.data as ComplianceLiveEvent)
          setLiveEvents((prev) => [parsed, ...prev].slice(0, maxEvents))
        } catch {
          /* ignore malformed */
        }
      },
    })

    return dispose
  }, [enabled, token, maxEvents])

  const graphAlerts = useMemo(
    () =>
      liveEvents
        .filter((ev) =>
          ['risk_score_changed', 'wallet_screened', 'alert_created', 'RiskRecalculated'].some(
            (t) => ev.type === t || ev.operator_event_type === t
          )
        )
        .map((ev) => ({
          nodeId: String(ev.payload?.address ?? ev.payload?.entity_key ?? ''),
          type: ev.operator_event_type ?? ev.type,
        }))
        .filter((a) => a.nodeId),
    [liveEvents]
  )

  const appendEvent = useCallback(
    (ev: ComplianceLiveEvent) => {
      setLiveEvents((prev) => [ev, ...prev].slice(0, maxEvents))
    },
    [maxEvents]
  )

  return {
    catalog: catalogQuery.data as OperatorEventCatalog | undefined,
    catalogLoading: catalogQuery.isLoading,
    liveEvents,
    graphAlerts,
    appendEvent,
    refetchCatalog: catalogQuery.refetch,
  }
}
