import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { complianceService } from '@/api/compliance-service'

const READ_ONLY_ROLES = new Set(['viewer'])

export type FusionPermissions = {
  effectiveRole: string
  permissions: string[]
  canExecute: boolean
  isViewer: boolean
  isLoading: boolean
}

/**
 * Compliance-plane RBAC for Fusion routes (MIO execute, workflow actions).
 * Uses existing GET /api/platform/v2/rbac/effective — API remains authoritative.
 */
export function useFusionPermissions(investigationId?: string): FusionPermissions {
  const query = useQuery({
    queryKey: ['fusion', 'rbac-effective', investigationId ?? 'global'],
    queryFn: () => complianceService.getRbacEffective(investigationId),
    staleTime: 5 * 60 * 1000,
    retry: 1,
  })

  return useMemo(() => {
    const effective = query.data?.effective_role ?? 'analyst'
    const permissions = query.data?.permissions ?? []
    const isViewer = READ_ONLY_ROLES.has(effective)
    const canExecute =
      !isViewer &&
      (permissions.includes('case:transition') ||
        permissions.includes('batch:screen') ||
        permissions.includes('case:create'))
    return {
      effectiveRole: effective,
      permissions,
      canExecute,
      isViewer,
      isLoading: query.isLoading,
    }
  }, [query.data, query.isLoading])
}
