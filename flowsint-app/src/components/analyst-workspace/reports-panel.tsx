import { useQuery } from '@tanstack/react-query'

import { complianceService } from '@/api/compliance-service'
import { EnterprisePanel } from '@/components/enterprise/enterprise-ui'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ExternalLink, FileText } from 'lucide-react'

type Props = {
  caseRef: string
}

export function ReportsPanel({ caseRef }: Props) {
  const reportsQuery = useQuery({
    queryKey: ['compliance', 'demo-reports', caseRef],
    queryFn: () => complianceService.listDemoReports(),
    retry: false,
  })

  const items = (reportsQuery.data ?? []).filter(
    (row) => !caseRef || row.case_ref === caseRef || !row.case_ref,
  )

  return (
    <EnterprisePanel
      title="Отчёты RFC-0005 / 115-ФЗ"
      description="Список сгенерированных отчётов из compliance API (демо / platform)."
    >
      {reportsQuery.isLoading ? (
        <Skeleton className="h-24 w-full" />
      ) : reportsQuery.isError ? (
        <p className="text-sm text-muted-foreground">
          Отчёты недоступны на этом стенде. Используйте экспорт через compliance API для кейса{' '}
          <span className="font-mono">{caseRef}</span>.
        </p>
      ) : items.length === 0 ? (
        <p className="text-sm text-muted-foreground">Нет готовых отчётов для связанного кейса.</p>
      ) : (
        <ul className="space-y-3 text-sm">
          {items.map((row) => (
            <li
              key={row.alert_id ?? row.report_id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-md border p-3"
            >
              <div>
                <div className="font-medium flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  {row.report_id ?? '—'}
                </div>
                <div className="text-muted-foreground text-xs mt-1">
                  {row.typology_code} · {row.decision_ru ?? row.alert_code}
                </div>
              </div>
              <div className="flex items-center gap-2">
                {row.risk_level ? <Badge variant="outline">{row.risk_level}</Badge> : null}
                {row.alert_id ? (
                  <Button variant="outline" size="sm" asChild>
                    <a
                      href={`${import.meta.env.VITE_COMPLIANCE_API || ''}/api/inbox/${row.alert_id}/fz115/pdf`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      PDF <ExternalLink className="w-3 h-3 ml-1" />
                    </a>
                  </Button>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}
    </EnterprisePanel>
  )
}
