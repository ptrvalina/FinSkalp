import { describe, expect, it, vi } from 'vitest'

import { runMioBatch } from '@/fusion/fusion-mio-batch'
import type { MioExecutableCard } from '@/fusion/fusion-mio-actions'

function card(id: string): MioExecutableCard {
  return {
    id,
    title: id,
    priority: 'medium',
    actionKind: 'refresh_graph',
  } as MioExecutableCard
}

describe('runMioBatch cancel + partial', () => {
  it('continues after failure and reports partial', async () => {
    const result = await runMioBatch(
      [card('a'), card('b'), card('c')],
      async (c) => {
        if (c.id === 'b') throw new Error('boom')
      }
    )
    expect(result.succeeded).toEqual(['a', 'c'])
    expect(result.failed).toEqual([{ cardId: 'b', error: 'boom' }])
  })

  it('stops when shouldCancel becomes true', async () => {
    let cancel = false
    const spy = vi.fn(async (c: MioExecutableCard) => {
      if (c.id === 'a') cancel = true
    })
    const result = await runMioBatch([card('a'), card('b'), card('c')], spy, undefined, {
      shouldCancel: () => cancel,
    })
    expect(spy).toHaveBeenCalledTimes(1)
    expect(result.succeeded).toEqual(['a'])
    expect(result.failed.some((f) => f.cardId === '__cancelled__')).toBe(true)
  })
})
