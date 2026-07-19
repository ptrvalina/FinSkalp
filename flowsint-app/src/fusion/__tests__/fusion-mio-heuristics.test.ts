import { describe, expect, it } from 'vitest'

import {
  estimateStrProbability,
  inferHypothesisTag,
  confidenceMeter,
} from '../fusion-mio-heuristics'
import type { MioExecutableCard } from '../fusion-mio-actions'
import { fusionCopy } from '../fusion-copy'
import { replayStateLabelAtIndex } from '../fusion-graph-utils'

describe('fusion-mio-heuristics STR estimate', () => {
  it('returns null for non-filing cards', () => {
    const card: MioExecutableCard = {
      id: '1',
      title: 'Run fusion',
      actionKind: 'fuse',
      priority: 'high',
    }
    expect(estimateStrProbability(card)).toBeNull()
  })

  it('returns elevated probability for open_report critical cards', () => {
    const card: MioExecutableCard = {
      id: '2',
      title: 'Подготовить SAR по санкциям',
      actionKind: 'open_report',
      priority: 'critical',
      rationale: '115-ФЗ evidence ready',
    }
    const p = estimateStrProbability(card)
    expect(p).not.toBeNull()
    expect(p!).toBeGreaterThan(0.85)
  })

  it('infers structuring hypothesis from mixer text', () => {
    const card: MioExecutableCard = {
      id: '3',
      title: 'Mixer layer detected',
      actionKind: 'fuse',
      priority: 'medium',
    }
    expect(inferHypothesisTag(card)).toBe('структурирование')
  })
})

describe('fusion-copy completeness', () => {
  it('has Russian scrubber labels', () => {
    expect(fusionCopy.scrubber.noTemporalAnchors).toMatch(/ЯКОР/)
    expect(fusionCopy.eccf.steps.filed).toBe('SAR')
  })

  it('replay labels use Russian copy', () => {
    expect(replayStateLabelAtIndex([], 0, [])).toBe(fusionCopy.scrubber.noTemporalAnchors)
  })
})

describe('confidence meter', () => {
  it('orders critical above low', () => {
    expect(confidenceMeter('critical')).toBeGreaterThan(confidenceMeter('low'))
  })
})
