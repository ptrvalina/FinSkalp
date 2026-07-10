import { EnterprisePanel } from '@/components/enterprise/enterprise-ui'
import { Badge } from '@/components/ui/badge'
import { EntityCard } from '@/components/enterprise/enterprise-ui'
import { Wallet } from 'lucide-react'

type EvidenceItem = Record<string, unknown>

type Props = {
  evidenceItems?: EvidenceItem[]
  supportedChains?: string[]
  selectedEntityId?: string | null
  loading?: boolean
}

function extractWallets(items: EvidenceItem[]): Array<{ address: string; chain?: string; source?: string }> {
  const seen = new Set<string>()
  const wallets: Array<{ address: string; chain?: string; source?: string }> = []

  const push = (address: string, chain?: string, source?: string) => {
    const key = address.toLowerCase()
    if (!address || seen.has(key)) return
    seen.add(key)
    wallets.push({ address, chain, source })
  }

  for (const item of items) {
    const entityType = String(item.entity_type ?? item.type ?? '').toLowerCase()
    const value = String(item.entity_value ?? item.value ?? item.address ?? '')
    if (entityType.includes('wallet') || entityType.includes('address') || value.startsWith('T')) {
      push(value, String(item.chain ?? item.network ?? ''), String(item.source_type ?? item.source ?? 'evidence'))
    }
    const payload = item.payload as Record<string, unknown> | undefined
    if (payload?.address) {
      push(String(payload.address), String(payload.chain ?? ''), 'payload')
    }
  }
  return wallets
}

export function WalletsPanel({
  evidenceItems = [],
  supportedChains = [],
  selectedEntityId,
  loading,
}: Props) {
  const wallets = extractWallets(evidenceItems)
  if (selectedEntityId && !wallets.some((w) => w.address === selectedEntityId)) {
    wallets.unshift({ address: selectedEntityId, chain: supportedChains[0], source: 'selection' })
  }

  return (
    <EnterprisePanel
      title="Кошельки"
      description="Адреса из доказательств и текущего выбора — без изменения graph UI."
    >
      <div className="flex flex-wrap gap-2 mb-4">
        <Badge variant="outline" className="gap-1">
          <Wallet className="w-3 h-3" />
          {wallets.length} адресов
        </Badge>
        {supportedChains.map((chain) => (
          <Badge key={chain} variant="secondary">
            {chain}
          </Badge>
        ))}
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Загрузка…</p>
      ) : wallets.length === 0 ? (
        <p className="text-sm text-muted-foreground">Кошельки не найдены в доказательствах кейса.</p>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {wallets.map((w) => (
            <EntityCard
              key={w.address}
              compact
              entity={{
                title: w.address,
                subtitle: w.chain || 'chain unknown',
                attributes: [w.source ?? 'workspace', 'Wallet explorer pivot'],
                sources: ['Evidence', 'Workspace'],
                confidence: 70,
                risk: 'medium',
              }}
            />
          ))}
        </div>
      )}
    </EnterprisePanel>
  )
}
