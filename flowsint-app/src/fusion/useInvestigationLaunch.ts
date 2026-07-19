import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { toast } from 'sonner'

import {
  prepareInvestigation,
  type StartInvestigationParams,
} from './fusion-investigation-start'
import { fusionChildSearch } from './fusion-route-search'

/** Survives seed overlay unmount — launch + navigate from workspace shell. */
export function useInvestigationLaunch() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (params: StartInvestigationParams) => prepareInvestigation(params),
    onSuccess: (prepared) => {
      void queryClient.invalidateQueries({ queryKey: ['fusion', 'inbox'] })
      void queryClient.invalidateQueries({ queryKey: ['fusion', 'cases'] })
      toast.info(`Запуск расследования ${prepared.caseRef} — смотрите граф`)
      void navigate({
        to: '/dashboard/fusion/investigation/$caseRef',
        params: { caseRef: prepared.caseRef },
        search: fusionChildSearch(),
      })
    },
    onError: (err: Error) => toast.error(err.message),
  })
}
