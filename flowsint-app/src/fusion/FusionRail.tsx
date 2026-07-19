import { Link } from '@tanstack/react-router'
import { cn } from '@/lib/utils'
import { fusionOpsLensRoute } from './fusion-route-search'

export type FusionOpsLens = 'canvas' | 'queue' | 'collect' | 'vault' | 'brief' | 'tools'

type Section =
  | 'command'
  | 'investigate'
  | 'intelligence'
  | 'graph'
  | 'queue'
  | 'tools'
  | 'vault'
  | 'profile'
  | 'flows'
  | 'types'
  | 'enrichers'
  | 'reports'
  | 'legacy'

type Props = {
  activeSection?: Section
  activeLens?: FusionOpsLens
  onLensChange?: (lens: FusionOpsLens) => void
  caseRef?: string | null
  graphOs?: boolean
  queueBadgeCount?: number
}

const OPS_LENSES: Array<{ id: FusionOpsLens; glyph: string; label: string }> = [
  { id: 'canvas', glyph: '◉', label: 'Canvas' },
  { id: 'queue', glyph: '◎', label: 'Queue' },
  { id: 'collect', glyph: '⎈', label: 'Collect' },
  { id: 'brief', glyph: '▤', label: 'Brief' },
]

const PLATFORM_LINKS: Array<{
  id: Section
  glyph: string
  label: string
  href: string
  requiresCase?: boolean
}> = [
  { id: 'tools', glyph: '⎈', label: 'Scalpel', href: '/dashboard/tools' },
  { id: 'vault', glyph: '▣', label: 'Vault', href: '/dashboard/vault' },
  { id: 'flows', glyph: '⇋', label: 'Flows', href: '/dashboard/flows' },
  { id: 'types', glyph: '▤', label: 'Types', href: '/dashboard/custom-types' },
  { id: 'enrichers', glyph: '◎', label: 'Enrichers', href: '/dashboard/enrichers' },
  { id: 'reports', glyph: '▥', label: 'Reports', href: '/dashboard/fusion/reports' },
  { id: 'graph', glyph: '◇', label: 'Case', href: '/dashboard/fusion/investigate', requiresCase: true },
  { id: 'profile', glyph: '◌', label: 'Profile', href: '/dashboard/profile' },
]

export function FusionRail({
  activeSection = 'command',
  activeLens = 'canvas',
  onLensChange,
  caseRef,
  graphOs = false,
  queueBadgeCount,
}: Props) {
  if (graphOs) {
    return (
      <nav className="fusion-rail fusion-rail--graph-os" aria-label="FinSkalp Ops Deck">
        <div className="fusion-rail__brand" title="FinSkalp Graph OS">
          ФС
        </div>
        {OPS_LENSES.map((item) => {
          const route = fusionOpsLensRoute(item.id, caseRef)
          const isActive = activeLens === item.id
          return (
            <Link
              key={item.id}
              to={route.to}
              {...('params' in route ? { params: route.params } : {})}
              search={route.search}
              className={cn(
                'fusion-rail__link fusion-rail__link--labeled fusion-rail__link--canvas',
                isActive && 'fusion-rail__link--active',
                item.id === 'collect' && 'fusion-rail__link--primary'
              )}
              title={item.label}
              aria-label={item.label}
              onClick={() => onLensChange?.(item.id)}
            >
              <span className="fusion-rail__glyph" aria-hidden>
                {item.glyph}
              </span>
              <span className="fusion-rail__label">{item.label}</span>
              {item.id === 'queue' && queueBadgeCount != null && queueBadgeCount > 0 ? (
                <span className="fusion-rail__badge" aria-label={`${queueBadgeCount} in queue`}>
                  {queueBadgeCount > 99 ? '99+' : queueBadgeCount}
                </span>
              ) : null}
            </Link>
          )
        })}
        <div className="fusion-rail__spacer flex-1 min-h-2" />
        {PLATFORM_LINKS.filter((s) => !s.requiresCase || caseRef).map((section) => {
          const href =
            section.id === 'graph' && caseRef
              ? `/dashboard/fusion/investigation/${encodeURIComponent(caseRef)}`
              : section.href
          const isActive = section.id === activeSection
          return (
            <Link
              key={section.id}
              to={href}
              className={cn(
                'fusion-rail__link fusion-rail__link--labeled',
                isActive && 'fusion-rail__link--active'
              )}
              title={section.label}
              aria-label={section.label}
            >
              <span className="fusion-rail__glyph" aria-hidden>
                {section.glyph}
              </span>
              <span className="fusion-rail__label">{section.label}</span>
            </Link>
          )
        })}
      </nav>
    )
  }

  const LEGACY_SECTIONS: Array<{
    id: Section
    glyph: string
    label: string
    href: string
    requiresCase?: boolean
  }> = [
    { id: 'command', glyph: '⌁', label: 'Командный центр', href: '/dashboard/fusion' },
    { id: 'investigate', glyph: '◈', label: 'Новое расследование', href: '/dashboard/fusion/investigate' },
    { id: 'graph', glyph: '◇', label: 'Открытое дело', href: '/dashboard/fusion/investigate', requiresCase: true },
    { id: 'tools', glyph: '⎈', label: 'Инструменты', href: '/dashboard/tools' },
    { id: 'vault', glyph: '▣', label: 'Хранилище', href: '/dashboard/vault' },
    { id: 'flows', glyph: '⇋', label: 'Потоки', href: '/dashboard/flows' },
    { id: 'types', glyph: '▤', label: 'Схемы', href: '/dashboard/custom-types' },
    { id: 'enrichers', glyph: '◎', label: 'Обогатители', href: '/dashboard/enrichers' },
    { id: 'profile', glyph: '◉', label: 'Профиль', href: '/dashboard/profile' },
  ]

  return (
    <nav className="fusion-rail" aria-label="Навигация FinSkalp">
      <div className="fusion-rail__brand" title="FinSkalp Fusion OS">
        ФС
      </div>
      {LEGACY_SECTIONS.filter((section) => !section.requiresCase || caseRef).map((section) => {
        const href =
          section.id === 'graph' && caseRef
            ? `/dashboard/fusion/investigation/${encodeURIComponent(caseRef)}`
            : section.href
        const isActive = section.id === activeSection
        return (
          <Link
            key={section.id}
            to={href}
            className={cn(
              'fusion-rail__link fusion-rail__link--labeled',
              isActive && 'fusion-rail__link--active',
              section.id === 'investigate' && 'fusion-rail__link--primary'
            )}
            title={section.label}
            aria-label={section.label}
          >
            <span className="fusion-rail__glyph" aria-hidden>
              {section.glyph}
            </span>
            <span className="fusion-rail__label">{section.label}</span>
          </Link>
        )
      })}
    </nav>
  )
}
