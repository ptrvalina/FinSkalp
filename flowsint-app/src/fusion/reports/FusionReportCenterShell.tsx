import { Link } from '@tanstack/react-router'
import { cn } from '@/lib/utils'

import { fusionCopy } from '../fusion-copy'

import { REPORT_CATEGORIES } from './report-catalog'
import type { ReportCategory } from './report-types'

type Props = {
  caseRef?: string
  activeCategory?: ReportCategory | 'all'
  onCategoryChange?: (cat: ReportCategory | 'all') => void
  activeView?: 'modules' | 'export' | 'presentation'
  children: React.ReactNode
}

export function FusionReportCenterShell({
  caseRef,
  activeCategory = 'all',
  onCategoryChange,
  activeView = 'modules',
  children,
}: Props) {
  return (
    <div
      className="fusion-report-center"
      data-testid="fusion-report-center"
      data-case-ref={caseRef ?? undefined}
    >
      <aside className="fusion-report-center__sidebar" aria-label="Report navigation">
        <div className="fusion-report-center__sidebar-head">
          <span className="fusion-text-micro text-[var(--fusion-text-tertiary)] uppercase tracking-widest">
            {fusionCopy.reports.sidebarTitle}
          </span>
          {caseRef ? (
            <Link
              to="/dashboard/fusion/investigation/$caseRef"
              params={{ caseRef }}
              className="fusion-mono fusion-text-micro text-[var(--fusion-ops-blue)] block mt-1 truncate"
            >
              {caseRef}
            </Link>
          ) : (
            <span className="fusion-text-micro text-[var(--fusion-text-tertiary)]">
              {fusionCopy.reports.selectCase}
            </span>
          )}
        </div>

        <nav className="fusion-report-center__nav">
          {caseRef ? (
            <>
              <Link
                to="/dashboard/fusion/reports/$caseRef"
                params={{ caseRef }}
                className={cn(
                  'fusion-report-center__nav-link',
                  activeView === 'modules' && 'fusion-report-center__nav-link--active'
                )}
              >
                {fusionCopy.reports.moduleGrid}
              </Link>
              <Link
                to="/dashboard/fusion/reports/$caseRef/$reportType"
                params={{ caseRef, reportType: 'export-center' }}
                className={cn(
                  'fusion-report-center__nav-link',
                  activeView === 'export' && 'fusion-report-center__nav-link--active'
                )}
              >
                {fusionCopy.reports.exportHub}
              </Link>
              <Link
                to="/dashboard/fusion/reports/$caseRef/$reportType"
                params={{ caseRef, reportType: 'presentation-mode' }}
                className={cn(
                  'fusion-report-center__nav-link',
                  activeView === 'presentation' && 'fusion-report-center__nav-link--active'
                )}
              >
                {fusionCopy.reports.presentationMode}
              </Link>
            </>
          ) : null}
        </nav>

        {caseRef && onCategoryChange ? (
          <div className="fusion-report-center__filters">
            <span className="fusion-text-micro text-[var(--fusion-text-tertiary)] uppercase">
              {fusionCopy.reports.categories}
            </span>
            <button
              type="button"
              className={cn(
                'fusion-report-center__filter',
                activeCategory === 'all' && 'fusion-report-center__filter--active'
              )}
              onClick={() => onCategoryChange('all')}
            >
              {fusionCopy.reports.filterAll}
            </button>
            {REPORT_CATEGORIES.map((c) => (
              <button
                key={c.id}
                type="button"
                className={cn(
                  'fusion-report-center__filter',
                  activeCategory === c.id && 'fusion-report-center__filter--active'
                )}
                onClick={() => onCategoryChange(c.id)}
              >
                {c.label}
              </button>
            ))}
          </div>
        ) : null}
      </aside>
      <main className="fusion-report-center__main">{children}</main>
    </div>
  )
}
