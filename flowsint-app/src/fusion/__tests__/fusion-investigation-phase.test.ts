import { describe, expect, it } from 'vitest'

import { resolveInvestigationPhase } from '../fusion-investigation-phase'

describe('resolveInvestigationPhase', () => {
  it('starts at seed when empty', () => {
    const p = resolveInvestigationPhase({
      hasSeed: false,
      nodeCount: 0,
      pipelineActive: false,
      pipelineError: false,
      kytDone: false,
      kytApplicable: true,
      fusionDone: false,
    })
    expect(p.currentId).toBe('seed')
    expect(p.nextActionKind).toBe('collect')
  })

  it('moves to fusion when graph and kyt done', () => {
    const p = resolveInvestigationPhase({
      hasSeed: true,
      nodeCount: 15,
      pipelineActive: false,
      pipelineError: false,
      kytDone: true,
      kytApplicable: true,
      fusionDone: false,
    })
    expect(p.currentId).toBe('fusion')
    expect(p.nextActionKind).toBe('fuse')
    expect(p.nowLabel).toContain('4/5')
  })

  it('stays on kyt until screened', () => {
    const p = resolveInvestigationPhase({
      hasSeed: true,
      nodeCount: 15,
      pipelineActive: false,
      pipelineError: false,
      kytDone: false,
      kytApplicable: true,
      fusionDone: false,
    })
    expect(p.currentId).toBe('kyt')
    expect(p.nextActionKind).toBe('kyt')
  })

  it('skips kyt gate when fusion already completed', () => {
    const p = resolveInvestigationPhase({
      hasSeed: true,
      nodeCount: 15,
      pipelineActive: false,
      pipelineError: false,
      kytDone: false,
      kytApplicable: true,
      fusionDone: true,
    })
    expect(p.currentId).toBe('reports')
    expect(p.nextActionKind).toBe('reports')
    expect(p.stages.find((s) => s.id === 'kyt')?.status).toBe('done')
  })
})
