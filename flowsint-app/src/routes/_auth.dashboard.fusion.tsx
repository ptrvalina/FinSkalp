import { createFileRoute, Outlet } from '@tanstack/react-router'

/** Layout shell for Mission Control, Investigation, Reports under /dashboard/fusion. */
export const Route = createFileRoute('/_auth/dashboard/fusion')({
  component: FusionLayoutRoute,
})

function FusionLayoutRoute() {
  return <Outlet />
}
