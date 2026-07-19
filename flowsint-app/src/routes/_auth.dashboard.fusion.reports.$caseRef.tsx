import { createFileRoute, Outlet } from '@tanstack/react-router'

/** Per-case report shell — index = module grid, child = document view. */
export const Route = createFileRoute('/_auth/dashboard/fusion/reports/$caseRef')({
  component: FusionReportCaseLayoutRoute,
})

function FusionReportCaseLayoutRoute() {
  return <Outlet />
}
