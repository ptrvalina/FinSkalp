import { createFileRoute, Outlet } from '@tanstack/react-router'

/** Layout for Report Center hub + per-case report modules. */
export const Route = createFileRoute('/_auth/dashboard/fusion/reports')({
  component: FusionReportsLayoutRoute,
})

function FusionReportsLayoutRoute() {
  return <Outlet />
}
