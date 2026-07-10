import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'

import { complianceService } from '@/api/compliance-service'
import { EnterprisePanel } from '@/components/enterprise/enterprise-ui'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { MessageSquare, Sparkles } from 'lucide-react'

type Props = {
  caseRef: string
  investigationId: string
}

export function AiContextPanel({ caseRef, investigationId: _investigationId }: Props) {
  const [prompt, setPrompt] = useState('')

  const contextQuery = useQuery({
    queryKey: ['eia', 'context', caseRef],
    queryFn: () => complianceService.getEiaContext(caseRef),
    enabled: Boolean(caseRef),
  })

  const assistMutation = useMutation({
    mutationFn: () =>
      complianceService.runEiaAssist({
        taskType: 'investigation_summary',
        caseRef,
      }),
  })

  return (
    <EnterprisePanel
      title="AI Context"
      description="EIA investigation assistant — existing platform v2 APIs"
    >
      <div className="space-y-4">
        {contextQuery.isLoading ? (
          <Skeleton className="h-16 w-full" />
        ) : contextQuery.data?.ok ? (
          <div className="rounded-md border border-dashed p-3 text-sm text-muted-foreground">
            <p className="flex items-center gap-2 font-medium text-foreground">
              <Sparkles className="h-4 w-4" />
              Context loaded
            </p>
            {contextQuery.data.sources?.length ? (
              <p className="text-xs mt-2">Sources: {contextQuery.data.sources.join(', ')}</p>
            ) : null}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">EIA context unavailable for this case.</p>
        )}

        <div className="flex gap-2">
          <Input
            placeholder="Спросить AI-ассистента…"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && prompt.trim()) {
                assistMutation.mutate()
              }
            }}
          />
          <Button
            size="sm"
            disabled={!prompt.trim() || assistMutation.isPending}
            onClick={() => assistMutation.mutate()}
          >
            <MessageSquare className="h-4 w-4" />
          </Button>
        </div>

        {assistMutation.data?.ok && assistMutation.data.narrative_ru ? (
          <div className="rounded-md bg-muted/40 p-3 text-sm">{assistMutation.data.narrative_ru}</div>
        ) : null}

        {assistMutation.data?.requires_analyst_confirmation ? (
          <p className="text-xs text-muted-foreground italic">
            Требуется подтверждение аналитика (confidence{' '}
            {Math.round((assistMutation.data.confidence ?? 0) * 100)}%)
          </p>
        ) : null}
      </div>
    </EnterprisePanel>
  )
}
