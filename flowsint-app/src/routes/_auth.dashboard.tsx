import { ConfirmContextProvider } from '@/components/use-confirm-dialog'
import { createFileRoute, Outlet } from '@tanstack/react-router'

export const Route = createFileRoute('/_auth/dashboard')({
  component: DashboardPage,
})

function DashboardPage() {
  return (
    <ConfirmContextProvider>
      <Outlet />
    </ConfirmContextProvider>
  )
}
