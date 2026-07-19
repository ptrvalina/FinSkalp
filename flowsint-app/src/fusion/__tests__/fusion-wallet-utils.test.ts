import { describe, expect, it } from 'vitest'

import {
  buildWalletCaseRef,
  inferWalletChain,
  isLikelyWalletAddress,
  resolveChainsToScan,
} from '../fusion-wallet-utils'

const TRON = 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t'

describe('fusion-wallet-utils', () => {
  it('detects tron addresses', () => {
    expect(isLikelyWalletAddress(TRON)).toBe(true)
    expect(inferWalletChain(TRON)).toBe('tron')
  })

  it('detects eth addresses', () => {
    const addr = '0x1234567890123456789012345678901234567890'
    expect(isLikelyWalletAddress(addr)).toBe(true)
    expect(inferWalletChain(addr)).toBe('eth')
  })

  it('builds wallet case refs with WL prefix', () => {
    const ref = buildWalletCaseRef(TRON)
    expect(ref.startsWith('WL-')).toBe(true)
    expect(ref.length).toBeGreaterThan(6)
  })

  it('auto mode picks primary chain', () => {
    expect(resolveChainsToScan(TRON, 'auto')).toEqual(['tron'])
    expect(resolveChainsToScan('0x1234567890123456789012345678901234567890', 'auto')).toEqual([
      'eth',
    ])
  })

  it('all mode scans all valid networks for 0x', () => {
    expect(resolveChainsToScan('0x1234567890123456789012345678901234567890', 'all')).toEqual([
      'eth',
      'bsc',
      'polygon',
    ])
    expect(resolveChainsToScan(TRON, 'all')).toEqual(['tron'])
  })
})
