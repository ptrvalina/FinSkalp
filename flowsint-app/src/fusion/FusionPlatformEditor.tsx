import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

type Props = {
  children: ReactNode
  className?: string
  toolbar?: ReactNode
}

/** Wraps platform builders (flows, schema, enrichers) in fusion void — no shadcn bg-background leak. */
export function FusionPlatformEditor({ children, className, toolbar }: Props) {
  return (
    <div className={cn('fusion-platform-editor', className)}>
      {toolbar ? <div className="fusion-platform-editor__toolbar">{toolbar}</div> : null}
      <div className="fusion-platform-editor__body custom-scrollbar">{children}</div>
    </div>
  )
}
