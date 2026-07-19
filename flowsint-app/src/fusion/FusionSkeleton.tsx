import { cn } from '@/lib/utils'

type Props = {
  rows?: number
  variant?: 'row' | 'card' | 'graph'
  className?: string
}

export function FusionSkeleton({ rows = 5, variant = 'row', className }: Props) {
  if (variant === 'graph') {
    return (
      <div
        className={cn('fusion-skeleton fusion-skeleton--graph', className)}
        aria-busy="true"
        aria-label="Загрузка графа"
      >
        <div className="fusion-skeleton__graph-pulse" />
        <span className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
          ЗАГРУЗКА ГРАФА…
        </span>
      </div>
    )
  }

  if (variant === 'card') {
    return (
      <div className={cn('grid gap-3 md:grid-cols-2 xl:grid-cols-3', className)} aria-busy="true">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="fusion-skeleton fusion-skeleton--card h-28" />
        ))}
      </div>
    )
  }

  return (
    <div className={cn('space-y-2', className)} aria-busy="true">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="fusion-skeleton fusion-skeleton--row h-8" />
      ))}
    </div>
  )
}
