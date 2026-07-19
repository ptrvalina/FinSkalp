// @vitest-environment happy-dom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

vi.mock('@tanstack/react-router', () => ({
  useNavigate: () => vi.fn(),
  Link: ({ children }: { children: React.ReactNode }) => <a>{children}</a>,
}))

vi.mock('@/hooks/use-compliance-events', () => ({
  useComplianceEvents: () => ({ liveEvents: [], graphAlerts: [], catalog: undefined }),
}))

vi.mock('@/hooks/use-fusion-permissions', () => ({
  useFusionPermissions: () => ({
    canExecute: true,
    isViewer: false,
    effectiveRole: 'analyst',
    permissions: ['case:transition'],
    isLoading: false,
  }),
}))

vi.mock('sigma', () => ({
  default: class MockSigma {
    constructor() {}
    kill() {}
    on() { return this }
    getCamera() { return { x: 0, y: 0, ratio: 1 } }
    setSetting() {}
    refresh() {}
  },
}))

vi.mock('@/api/compliance-service', () => ({
  complianceService: {
    listInbox: vi.fn().mockResolvedValue([]),
    getWorkflowStats: vi.fn().mockResolvedValue({ total: 0, sla_breached: 0, pipeline: {} }),
    getCase: vi.fn(),
    getGraph: vi.fn(),
    getCaseRiskHistory: vi.fn().mockResolvedValue({ points: [] }),
    getWorkflowRecommendations: vi.fn().mockResolvedValue({ recommendations: [] }),
    getCaseTimeline: vi.fn().mockResolvedValue({ events: [] }),
    getAnalystWorkspaceState: vi.fn().mockResolvedValue({ evidence: { items: [] }, timeline: { events: [] } }),
  },
}))

import { FusionMissionControlWorkspace } from '../mission-control/FusionMissionControlWorkspace'

describe('FusionMissionControlWorkspace render', () => {
  it('mounts without throwing', () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    expect(() =>
      render(
        <QueryClientProvider client={qc}>
          <FusionMissionControlWorkspace />
        </QueryClientProvider>
      )
    ).not.toThrow()
  })
})
