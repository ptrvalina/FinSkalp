import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

type Props = {
  title: string
  description?: string
  icon?: ReactNode
  action?: ReactNode
  className?: string
}

export function FusionEmptyState({ title, description, icon, action, className }: Props) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center px-6 py-12 text-center',
        className
      )}
    >
      {icon ? (
        <div className="mb-3 text-[var(--fusion-text-tertiary)] [&_svg]:h-8 [&_svg]:w-8">
          {icon}
        </div>
      ) : null}
      <p className="fusion-text-data text-[var(--fusion-text-primary)]">{title}</p>
      {description ? (
        <p className="fusion-text-micro mt-2 max-w-md text-[var(--fusion-text-secondary)]">
          {description}
        </p>
      ) : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  )
}
