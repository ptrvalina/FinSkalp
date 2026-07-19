import { cn } from '@/lib/utils'

type Props = {
  message: string
  className?: string
  assertive?: boolean
}

export function FusionInlineError({ message, className, assertive = true }: Props) {
  return (
    <p
      role={assertive ? 'alert' : 'status'}
      className={cn(
        'fusion-inline-error fusion-text-micro fusion-tone-critical',
        className
      )}
    >
      {message}
    </p>
  )
}
