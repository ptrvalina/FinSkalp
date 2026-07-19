import { Navigate, createFileRoute } from '@tanstack/react-router'
import { InvestigationSkeleton } from '@/components/dashboard/investigation/investigation-skeleton'

export const Route = createFileRoute('/_auth/dashboard/')({
  component: () => <Navigate to="/dashboard/fusion" />,
  pendingComponent: InvestigationSkeleton,
})
