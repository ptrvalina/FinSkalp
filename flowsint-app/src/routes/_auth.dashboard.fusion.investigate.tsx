import { createFileRoute, Navigate } from '@tanstack/react-router'
import { fusionMissionSearch } from '@/fusion/fusion-route-search'

/** Canonical seed ingress — opens Collect lens on Mission Control Graph OS. */
export const Route = createFileRoute('/_auth/dashboard/fusion/investigate')({
  component: InvestigateRedirectPage,
})

function InvestigateRedirectPage() {
  return <Navigate to="/dashboard/fusion" search={fusionMissionSearch('collect')} replace />
}