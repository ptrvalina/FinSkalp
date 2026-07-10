import type { ItemType } from '@/stores/node-display-settings'

const ITEM_TYPES = new Set<string>([
  'domain',
  'email',
  'ip',
  'phone',
  'username',
  'organization',
  'individual',
  'socialaccount',
  'asn',
  'cidr',
  'cryptowallet',
  'cryptowallettransaction',
  'cryptonft',
  'website',
  'port',
  'phrase',
  'breach',
  'credential',
  'device',
  'document',
  'file',
  'malware',
  'sslcertificate',
  'location',
  'affiliation',
  'bankaccount',
  'vehicle',
  'vulnerability',
  'whois',
  'leak',
  'company',
  'person',
  'wallet',
  'address',
  'url',
  'hash',
  'cve',
  'software',
  'service',
  'registry',
  'sanction',
  'note',
  'event',
  'transaction',
  'account',
  'alias',
  'custom',
])

export function asItemType(value: string): ItemType {
  return (ITEM_TYPES.has(value) ? value : 'custom') as ItemType
}

export function lookupItemTypeRecord<T>(record: Record<ItemType, T>, key: string): T | undefined {
  return record[asItemType(key)]
}
