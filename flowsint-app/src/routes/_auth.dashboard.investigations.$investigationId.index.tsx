import { Navigate, createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/_auth/dashboard/investigations/$investigationId/')({
  component: () => <Navigate to="/dashboard/fusion" replace />,
})
