import { Navigate, createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/_auth/dashboard/compliance')({
  validateSearch: (search: Record<string, unknown>) => ({
    caseRef: typeof search.caseRef === 'string' ? search.caseRef : undefined,
  }),
  component: ComplianceLegacyRedirect,
})

function ComplianceLegacyRedirect() {
  const { caseRef } = Route.useSearch()
  if (caseRef) {
    return (
      <Navigate
        to="/dashboard/fusion/investigation/$caseRef"
        params={{ caseRef }}
        replace
      />
    )
  }
  return <Navigate to="/dashboard/fusion" replace />
}
