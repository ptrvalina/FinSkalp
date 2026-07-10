import {
  ChevronLeft,
  ChevronRight,
  Home,
  Lock,
  Shield,
  type LucideIcon,
  Shapes,
  SquareKanban,
  UserRound,
  Wrench,
  Workflow,
  Puzzle,
} from 'lucide-react'
import { Link, useLocation } from '@tanstack/react-router'
import { useLayoutStore } from '@/stores/layout-store'
import { Button } from '../ui/button'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip'
import { memo, useMemo, useState } from 'react'
import { NavUser } from '../nav-user'
import { CONFIG } from '@/config'
import { cn } from '@/lib/utils'

interface NavItem {
  icon: LucideIcon
  label: string
  href?: string
  section: 'Workspace' | 'Operations'
}

export const Sidebar = memo(() => {
  const togglePanel = useLayoutStore((s) => s.togglePanel)
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)

  const navItems: NavItem[] = [
    { icon: Home, label: 'Command Center', href: '/dashboard/', section: 'Workspace' },
    { icon: Shield, label: 'Compliance', href: '/dashboard/compliance', section: 'Workspace' },
    { icon: Workflow, label: 'Flow Architect', href: '/dashboard/flows', section: 'Workspace' },
    {
      icon: Shapes,
      label: 'Schema Architect',
      href: '/dashboard/custom-types',
      section: 'Workspace',
    },
    { icon: Lock, label: 'Vault', href: '/dashboard/vault', section: 'Operations' },
    { icon: Wrench, label: 'Forensic Toolset', href: '/dashboard/tools', section: 'Operations' },
    { icon: UserRound, label: 'User Profile', href: '/dashboard/profile', section: 'Operations' },
  ]

  if (CONFIG.ENRICHER_TEMPLATES_FEATURE_FLAG)
    navItems.push({
      icon: Puzzle,
      label: 'Enrichers',
      href: '/dashboard/enrichers',
      section: 'Operations',
    })

  const groupedItems = useMemo(
    () =>
      navItems.reduce<Record<string, NavItem[]>>((acc, item) => {
        if (!acc[item.section]) {
          acc[item.section] = []
        }
        acc[item.section].push(item)
        return acc
      }, {}),
    [navItems]
  )

  return (
    <aside
      className={cn(
        'flex h-full shrink-0 flex-col border-r border-[var(--fs-border)] bg-[var(--fs-bg-secondary)] transition-[width]',
        collapsed ? 'w-18' : 'w-64'
      )}
    >
      <div className="border-b border-[var(--fs-border)] px-3 py-4">
        <div className="flex items-center justify-between gap-2">
          <div className={cn('min-w-0', collapsed && 'hidden')}>
            <p className="text-sm font-semibold tracking-[0.08em] text-[var(--fs-text-primary)]">
              FinSkalp
            </p>
            <p className="mt-1 text-[11px] uppercase tracking-[0.16em] text-[var(--fs-text-tertiary)]">
              Investigation Workspace
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setCollapsed((prev) => !prev)}
            className="h-8 w-8 rounded-sm border border-[var(--fs-border)] text-[var(--fs-text-secondary)]"
          >
            {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-2 py-3">
        {Object.entries(groupedItems).map(([section, items]) => (
          <div key={section} className="mb-5">
            {!collapsed ? (
              <p className="px-2 pb-2 text-[11px] uppercase tracking-[0.16em] text-[var(--fs-text-tertiary)]">
                {section}
              </p>
            ) : null}
            <div className="space-y-1">
              {items.map((item) => {
                const Icon = item.icon
                const active = item.href
                  ? location.pathname === item.href || location.pathname.startsWith(`${item.href}/`)
                  : false
                const linkBody = (
                  <span
                    className={cn(
                      'relative flex h-10 items-center gap-3 rounded-sm border border-transparent px-3 text-sm text-[var(--fs-text-secondary)] transition-colors hover:bg-[var(--fs-surface)] hover:text-[var(--fs-text-primary)]',
                      active &&
                        'border-[var(--fs-border)] bg-[var(--fs-surface)] text-[var(--fs-text-primary)] before:absolute before:bottom-1 before:left-0 before:top-1 before:w-0.5 before:bg-[var(--fs-accent)]'
                    )}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    {!collapsed ? <span className="truncate">{item.label}</span> : null}
                  </span>
                )

                return (
                  <TooltipProvider key={item.label}>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        {item.href ? <Link to={item.href}>{linkBody}</Link> : <button>{linkBody}</button>}
                      </TooltipTrigger>
                      {collapsed ? <TooltipContent side="right">{item.label}</TooltipContent> : null}
                    </Tooltip>
                  </TooltipProvider>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="space-y-3 border-t border-[var(--fs-border)] p-3">
        <Button
          variant="ghost"
          onClick={togglePanel}
          className="flex h-9 w-full items-center justify-start gap-3 rounded-sm border border-[var(--fs-border)] px-3 text-[var(--fs-text-secondary)] hover:bg-[var(--fs-surface)] hover:text-[var(--fs-text-primary)]"
        >
          <SquareKanban className="h-4 w-4" />
          {!collapsed ? <span>Toggle Context Panel</span> : null}
        </Button>
        {!collapsed ? <NavUser /> : <div className="flex justify-center"><NavUser /></div>}
      </div>
    </aside>
  )
})
