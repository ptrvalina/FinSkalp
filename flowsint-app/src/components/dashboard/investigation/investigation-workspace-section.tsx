import { useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { Briefcase } from 'lucide-react'
import { complianceService } from '@/api/compliance-service'
import { useInvestigationUiContext } from '@/design-system'
import { AnalystWorkspaceShell } from '@/components/analyst-workspace'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { toast } from 'sonner'

type Props = {
  investigationId: string
  investigationName: string
}

export function InvestigationWorkspaceSection({ investigationId, investigationName }: Props) {
  const { setInvestigationId, setCaseRef } = useInvestigationUiContext()
  const queryClient = useQueryClient()

  useEffect(() => {
    setInvestigationId(investigationId)
  }, [investigationId, setInvestigationId])

  const linkedCaseQuery = useQuery({
    queryKey: ['compliance', 'case-by-investigation', investigationId],
    queryFn: () => complianceService.findCaseByInvestigationId(investigationId),
    retry: false
  })

  const caseRef = linkedCaseQuery.data?.case_ref ?? null

  useEffect(() => {
    setCaseRef(caseRef)
  }, [caseRef, setCaseRef])

  const createCaseMutation = useMutation({
    mutationFn: () => {
      const slug = investigationName
        .trim()
        .replace(/\s+/g, '-')
        .replace(/[^a-zA-Z0-9а-яА-Я-]/g, '')
        .slice(0, 32)
      const ref = `INV-${slug || investigationId.slice(0, 8)}`
      return complianceService.createCase(ref, investigationId)
    },
    onSuccess: (created) => {
      toast.success(`Кейс ${created.case_ref} связан с расследованием`)
      queryClient.invalidateQueries({
        queryKey: ['compliance', 'case-by-investigation', investigationId]
      })
    },
    onError: (error) => {
      toast.error(
        error instanceof Error ? error.message : 'Не удалось создать кейс комплаенса'
      )
    }
  })

  if (linkedCaseQuery.isLoading) {
    return (
      <AnalystWorkspaceShell
        investigationId={investigationId}
        investigationName={investigationName}
        caseRef={null}
        linkedCaseLoading
      />
    )
  }

  if (!linkedCaseQuery.data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Briefcase className="w-4 h-4" />
            Рабочее пространство аналитика
          </CardTitle>
          <CardDescription>
            Свяжите расследование с кейсом комплаенса для единого рабочего пространства RFC-0010.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button
            size="sm"
            onClick={() => createCaseMutation.mutate()}
            disabled={createCaseMutation.isPending}
          >
            Создать кейс комплаенса
          </Button>
          <Button size="sm" variant="outline" asChild>
            <Link to="/dashboard/compliance">Открыть комплаенс</Link>
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <AnalystWorkspaceShell
      investigationId={investigationId}
      investigationName={investigationName}
      caseRef={caseRef}
    />
  )
}
