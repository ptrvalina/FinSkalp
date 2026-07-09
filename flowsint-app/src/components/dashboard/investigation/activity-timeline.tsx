import { Clock } from "lucide-react"

export type TimelineEvent = {
  id: string
  event_type: string
  occurred_at: string
  actor?: string
  payload?: Record<string, unknown>
}

type Props = {
  events?: TimelineEvent[]
  loading?: boolean
}

function formatTime(iso: string) {
  try {
    return new Date(iso).toLocaleString("ru-RU")
  } catch {
    return iso
  }
}

export function ActivityTimeline({ events, loading }: Props) {
  const list = events ?? []

  return (
    <section>
      <h3 className="text-sm font-medium text-foreground mb-3">Хронология</h3>
      {loading ? (
        <p className="text-sm text-muted-foreground">Загрузка…</p>
      ) : list.length === 0 ? (
        <p className="text-sm text-muted-foreground">Событий пока нет</p>
      ) : (
        <div className="space-y-2">
          {list.map((event) => (
            <div key={event.id} className="flex items-start gap-3 py-2 text-sm">
              <Clock className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
              <div className="flex-1 min-w-0">
                <span className="text-foreground">{event.event_type}</span>
                {event.actor && (
                  <span className="text-muted-foreground"> · {event.actor}</span>
                )}
                <span className="text-muted-foreground/60 ml-2">{formatTime(event.occurred_at)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
