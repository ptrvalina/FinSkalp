import { describe, expect, it } from 'vitest'

import {
  buildCaseRefFromSeed,
  defaultCollectorsForSeed,
  parseSeedPool,
  personToUsernames,
  primaryWallet,
  scalpelTargetAddress,
  seedUsernames,
  workflowSeedFromItems,
} from '../fusion-investigation-seed'

const TRON = 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t'

describe('parseSeedPool', () => {
  it('parses typed lines', () => {
    const items = parseSeedPool(
      'wallet:TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t\nperson:Иванов Алексей\norg:ООО Пример'
    )
    expect(items).toEqual([
      { type: 'wallet', value: TRON },
      { type: 'person', value: 'Иванов Алексей' },
      { type: 'organization', value: 'ООО Пример' },
    ])
  })

  it('detects bare wallet addresses', () => {
    const items = parseSeedPool(TRON)
    expect(items[0]).toMatchObject({ type: 'wallet', value: TRON, chain: 'tron' })
  })

  it('treats multi-word lines as person names', () => {
    const items = parseSeedPool('Иванов Алексей')
    expect(items[0]).toEqual({ type: 'person', value: 'Иванов Алексей' })
  })

  it('treats single tokens as organizations', () => {
    const items = parseSeedPool('AcmeCorp')
    expect(items[0]).toEqual({ type: 'organization', value: 'AcmeCorp' })
  })

  it('skips comments and blank lines', () => {
    const items = parseSeedPool('# comment\n\nusername:myhandle')
    expect(items).toEqual([{ type: 'username', value: 'myhandle' }])
  })
})

describe('seed helpers', () => {
  it('derives Latin Maigret usernames from Cyrillic FIO', () => {
    const names = personToUsernames('Иванов Алексей')
    expect(names).toEqual(
      expect.arrayContaining(['ivanov', 'ivanov_aleksey', 'aleksey_ivanov', 'aivanov'])
    )
    expect(names.every((n) => /^[a-z0-9._-]+$/.test(n))).toBe(true)
  })

  it('keeps given name for three-part FIO (not patronymic as last)', () => {
    const names = personToUsernames('Иванов Алексей Петрович')
    expect(names).toContain('ivanov_aleksey')
    expect(names).not.toContain('petrovich')
  })

  it('detects ООО … as organization even with spaces', () => {
    expect(parseSeedPool('ООО Ромашка')[0]).toEqual({
      type: 'organization',
      value: 'ООО Ромашка',
    })
  })

  it('collects Latin usernames from Cyrillic person seed', () => {
    const items = parseSeedPool('person:Иванов Алексей\nusername:myhandle')
    expect(seedUsernames(items)).toEqual(expect.arrayContaining(['myhandle', 'ivanov_aleksey']))
  })

  it('builds case refs by seed type', () => {
    expect(buildCaseRefFromSeed([{ type: 'wallet', value: TRON }])).toMatch(/^WL-/)
    expect(buildCaseRefFromSeed([{ type: 'person', value: 'Иванов' }])).toMatch(/^PR-/)
    expect(buildCaseRefFromSeed([{ type: 'organization', value: 'Acme' }])).toMatch(/^ORG-/)
  })

  it('resolves scalpel target for non-wallet seeds', () => {
    const items = parseSeedPool('person:Иванов')
    expect(primaryWallet(items)).toBeNull()
    expect(scalpelTargetAddress(items)).toMatch(/^person:/)
  })

  it('picks collectors based on seed mix', () => {
    const walletItems = parseSeedPool(`wallet:${TRON}`)
    expect(defaultCollectorsForSeed(walletItems)).toContain('onchain_explorer')
    expect(defaultCollectorsForSeed(walletItems)).toContain('darknet_index')
    expect(defaultCollectorsForSeed(walletItems)).toContain('court_enforcement')

    const personItems = parseSeedPool('person:Иванов')
    expect(defaultCollectorsForSeed(personItems)).toContain('username_social')
    expect(defaultCollectorsForSeed(personItems)).toContain('username_probe')
    expect(defaultCollectorsForSeed(personItems)).toContain('sanctions_watchlist')
    expect(defaultCollectorsForSeed(personItems)).not.toContain('onchain_explorer')

    const orgItems = parseSeedPool('org:ООО Пример')
    expect(defaultCollectorsForSeed(orgItems)).toEqual(
      expect.arrayContaining(['sanctions_watchlist', 'clearnet_intel', 'vasp_registry', 'darknet_index'])
    )
  })

  it('maps workflow seed from items', () => {
    expect(workflowSeedFromItems(parseSeedPool(`wallet:${TRON}`))).toEqual({
      seed_type: 'wallet',
      seed_value: TRON,
      chain: 'tron',
    })
  })
})
