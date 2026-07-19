import { describe, expect, it } from 'vitest'

import {
  fusionLensFromSearch,
  fusionMissionSearch,
  fusionOpsLensRoute,
} from '@/fusion/fusion-route-search'

describe('fusion-route-search', () => {
  it('maps lens search params', () => {
    expect(fusionMissionSearch()).toEqual({ lens: undefined })
    expect(fusionMissionSearch('collect')).toEqual({ lens: 'collect' })
    expect(fusionLensFromSearch('brief')).toBe('brief')
    expect(fusionLensFromSearch(undefined)).toBe('canvas')
  })

  it('routes platform ops lenses to mission control without case', () => {
    expect(fusionOpsLensRoute('canvas')).toEqual({
      to: '/dashboard/fusion',
      search: { lens: undefined },
    })
    expect(fusionOpsLensRoute('collect')).toEqual({
      to: '/dashboard/fusion',
      search: { lens: 'collect' },
    })
    expect(fusionOpsLensRoute('queue')).toEqual({
      to: '/dashboard/fusion',
      search: { lens: 'queue' },
    })
  })

  it('routes ops lenses to active investigation when case ref exists', () => {
    expect(fusionOpsLensRoute('canvas', 'FSK-BF-2026-0709-001')).toEqual({
      to: '/dashboard/fusion/investigation/$caseRef',
      params: { caseRef: 'FSK-BF-2026-0709-001' },
      search: { lens: undefined },
    })
    expect(fusionOpsLensRoute('collect', 'FSK-BF-2026-0709-001')).toEqual({
      to: '/dashboard/fusion/investigation/$caseRef',
      params: { caseRef: 'FSK-BF-2026-0709-001' },
      search: { lens: 'collect' },
    })
  })
})
