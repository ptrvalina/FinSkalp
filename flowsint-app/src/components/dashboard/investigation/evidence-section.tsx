import { FileText } from "lucide-react"

export type EvidenceItem = {
  id: string
  source_type: string
  content_hash: string
  status: string
  payload?: Record<string, unknown>
}

type Props = {
  items?: EvidenceItem[]
  loading?: boolean
}

export function EvidenceSection({ items, loading }: Props) {
  const list = items ?? []

  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-medium text-foreground">Доказательства</h2>
        <span className="text-xs text-muted-foreground">{list.length} записей</span>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Загрузка…</p>
      ) : list.length === 0 ? (
        <p className="text-sm text-muted-foreground">Нет зарегистрированных доказательств</p>
      ) : (
        <div className="space-y-0.5">
          {list.map((item) => (
            <div
              key={item.id}
              className="group flex items-center gap-3 p-2 -mx-2 rounded hover:bg-secondary/50 transition-colors cursor-pointer"
            >
              <FileText className="w-4 h-4 text-muted-foreground shrink-0" />
              <span className="flex-1 text-sm text-foreground truncate">
                {(item.payload?.entity_value as string) || item.source_type}
              </span>
              <span className="text-xs text-muted-foreground">{item.status}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
