import type { ReactNode } from 'react'

import { Link } from '@tanstack/react-router'

import { FusionKeyboardProvider } from './FusionKeyboard'
import { FusionRail } from './FusionRail'
import { FusionZone } from './FusionZone'
import { loadLastCaseRef, WORKFLOW_LABELS } from './fusion-mission-data'

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

type Props = {
  children: ReactNode
  title: string
  subtitle?: string
  activeSection?: Section
  actions?: ReactNode
  caseRef?: string | null
  workflowStatus?: string | null
}

export function FusionPlatformShell({
  children,
  title,
  subtitle,
  activeSection = 'command',
  actions,
  caseRef,
  workflowStatus,
}: Props) {
  const returnCaseRef = caseRef ?? loadLastCaseRef()

  return (
    <FusionKeyboardProvider caseRef={caseRef}>
      <div className="fusion-root fusion-shell fusion-shell--graph-os fusion-platform-shell" data-fusion>
        <FusionRail activeSection={activeSection} caseRef={caseRef} />
        <div className="fusion-shell__main">
          <div className="fusion-intelligence-ribbon fusion-platform-ribbon">
            <span className="fusion-platform-ribbon__label">ПЛАТФОРМА</span>
            <span className="fusion-platform-ribbon__title">{title}</span>
            {subtitle ? (
              <span className="fusion-platform-ribbon__sub">{subtitle}</span>
            ) : null}
            {returnCaseRef ? (
              <nav
                className="fusion-platform-breadcrumb ml-3 flex items-center gap-2"
                aria-label="Продолжение расследования"
              >
                <Link
                  to="/dashboard/fusion/investigation/$caseRef"
                  params={{ caseRef: returnCaseRef }}
                  className="fusion-platform-return"
                >
                  ← Расследование
                </Link>
                <span className="fusion-mono fusion-text-micro text-[var(--fusion-ops-blue)]">
                  {returnCaseRef}
                </span>
                {workflowStatus ? (
                  <span className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
                    · {WORKFLOW_LABELS[workflowStatus] ?? workflowStatus}
                  </span>
                ) : null}
                <span className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
                  · контекст сохранён
                </span>
              </nav>
            ) : null}
            {actions ? <div className="fusion-platform-ribbon__actions">{actions}</div> : null}
          </div>
          <div className="fusion-shell__body fusion-platform-body">
            <FusionZone label={title} tone="ops" className="h-full flex-1 min-h-0">
              <div className="fusion-platform-content">{children}</div>
            </FusionZone>
          </div>
        </div>
      </div>
    </FusionKeyboardProvider>
  )
}
