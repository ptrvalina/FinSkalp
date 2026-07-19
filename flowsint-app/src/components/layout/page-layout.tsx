import React from 'react'

interface PageLayoutProps {
  title: string
  description?: string
  actions?: React.ReactNode
  children: React.ReactNode
  isLoading?: boolean
  loadingComponent?: React.ReactNode
  error?: Error | null
  errorComponent?: React.ReactNode
}

export function PageLayout({
  title,
  description,
  actions,
  children,
  isLoading,
  loadingComponent,
  error,
  errorComponent
}: PageLayoutProps) {
  return (
    <div className="h-full w-full overflow-y-auto bg-[var(--fusion-bg-void)]">
      <div className="sticky top-0 z-10 border-b border-[var(--fusion-border)] bg-[color-mix(in_srgb,var(--fusion-bg-void)_92%,transparent)] backdrop-blur">
        <div className="mx-auto max-w-7xl px-6 py-5 xl:px-8">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="space-y-1">
              <p className="text-[11px] uppercase tracking-[0.18em] text-[var(--fusion-text-tertiary)]">
                Enterprise workspace
              </p>
              <h1 className="text-2xl font-semibold text-[var(--fusion-text-primary)]">{title}</h1>
              {description && (
                <p className="max-w-3xl text-sm text-[var(--fusion-text-secondary)]">{description}</p>
              )}
            </div>
            {actions && <div className="flex items-center gap-2">{actions}</div>}
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-7xl space-y-6 px-6 py-6 xl:px-8">
        {isLoading ? loadingComponent : error ? errorComponent : children}
      </div>
    </div>
  )
}
