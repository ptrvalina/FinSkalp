import { describe, expect, it } from 'vitest'

import { buildMioCards } from '../fusion-mio-actions'

const BASE_RECS = [
  {
    id: 'run_collectors',
    action_ru: 'Запустить автоматический сбор данных',
    explanation_ru: 'collectors',
    priority: 'high',
  },
  {
    id: 'review_evidence',
    action_ru: 'Проверить доказательства',
    explanation_ru: 'evidence',
    priority: 'medium',
  },
  {
    id: 'build_graph',
    action_ru: 'Построить граф',
    explanation_ru: 'graph',
    priority: 'medium',
  },
]

describe('buildMioCards', () => {
  it('maps real-wallet run_collectors to run_scalpel', () => {
    const wallet = { address: 'TTestWalletAddress123456789012345678', chain: 'tron' }
    const cards = buildMioCards({
      recommendations: BASE_RECS,
      workflowStatus: 'new',
      fusionDone: false,
      investigationWallet: wallet,
      isDemoCase: false,
    })
    const collectors = cards.find((c) => c.id === 'run_collectors')
    expect(collectors?.actionKind).toBe('run_scalpel')
    expect(collectors?.walletAddress).toBe(wallet.address)
  })

  it('keeps demo run_collectors as fuse', () => {
    const cards = buildMioCards({
      recommendations: BASE_RECS,
      workflowStatus: 'new',
      fusionDone: false,
      isDemoCase: true,
    })
    expect(cards.find((c) => c.id === 'run_collectors')?.actionKind).toBe('fuse')
  })

  it('includes screen_wallet when seed wallet is set', () => {
    const wallet = { address: 'TSeedWallet123456789012345678901234', chain: 'tron' }
    const cards = buildMioCards({
      recommendations: [
        ...BASE_RECS,
        {
          id: 'screen_wallet',
          action_ru: 'Проверить кошелёк',
          explanation_ru: 'kyt',
          priority: 'critical',
        },
      ],
      investigationWallet: wallet,
      isDemoCase: false,
    })
    const screen = cards.filter((c) => c.id === 'screen_wallet')
    expect(screen.length).toBe(1)
    expect(screen[0]?.actionKind).toBe('screen_wallet')
    expect(screen[0]?.walletAddress).toBe(wallet.address)
  })

  it('maps review_evidence and build_graph to UI actions', () => {
    const cards = buildMioCards({
      recommendations: BASE_RECS,
      isDemoCase: false,
    })
    expect(cards.find((c) => c.id === 'review_evidence')?.actionKind).toBe('open_evidence')
    expect(cards.find((c) => c.id === 'build_graph')?.actionKind).toBe('refresh_graph')
  })
})
