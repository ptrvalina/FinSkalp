import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

type Tone = 'neutral' | 'ops' | 'clear' | 'caution' | 'critical'

type Props = {
  label: string
  tone?: Tone
  children: ReactNode
  className?: string
}

const TONE_CLASS: Record<Tone, string> = {
  neutral: '',
  ops: 'fusion-tone-ops',
  clear: 'fusion-tone-clear',
  caution: 'fusion-tone-caution',
  critical: 'fusion-tone-critical',
}

export function FusionZone({ label, tone = 'neutral', children, className }: Props) {
  return (
    <section className={cn('fusion-zone', className)}>
      <header className={cn('fusion-zone__label', TONE_CLASS[tone])}>{label}</header>
      <div className="fusion-zone__content">{children}</div>
    </section>
  )
}
