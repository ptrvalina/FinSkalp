import { createFileRoute, redirect } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { PlusIcon, FileCode2, Clock, FileX, Upload, FlaskConical, X } from 'lucide-react'
import { useNavigate } from '@tanstack/react-router'
import { toast } from 'sonner'
import { SkeletonList } from '@/components/shared/skeleton-list'
import { formatDistanceToNow } from 'date-fns'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import ErrorState from '@/components/shared/error-state'
import { templateService, type Template } from '@/api/template-service'
import { CONFIG } from '@/config'
import { FusionPlatformShell } from '@/fusion'

export const Route = createFileRoute('/_auth/dashboard/enrichers/')({
  beforeLoad: async () => {
    if (!CONFIG.ENRICHER_TEMPLATES_FEATURE_FLAG) {
      throw redirect({
        to: '/'
      })
    }
  },
  component: TemplatesPage
})

function TemplatesPage() {
  const navigate = useNavigate()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isBannerDismissed, setIsBannerDismissed] = useState(false)

  const {
    data: templates,
    isLoading,
    error,
    refetch
  } = useQuery<Template[]>({
    queryKey: ['template', 'enrichers'],
    queryFn: () => templateService.getAll()
  })

  const handleImportFile = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    if (!file.name.endsWith('.yaml') && !file.name.endsWith('.yml')) {
      toast.error('Only YAML files (.yaml, .yml) are supported')
      if (fileInputRef.current) fileInputRef.current.value = ''
      return
    }

    const reader = new FileReader()
    reader.onload = (e) => {
      const content = e.target?.result as string
      navigate({
        to: '/dashboard/enrichers/new',
        state: { importedContent: content }
      } as Parameters<typeof navigate>[0])
    }
    reader.onerror = () => {
      toast.error('Failed to read file')
    }
    reader.readAsText(file)

    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const categories =
    templates?.reduce((acc: string[], template) => {
      if (template.category && !acc.includes(template.category)) {
        acc.push(template.category)
      }
      return acc
    }, []) || []

  const allCategories = ['All', ...categories]

  return (
    <FusionPlatformShell
      title="Шаблоны обогатителей"
      subtitle="YAML-конфигурации пользовательских enricher"
      activeSection="enrichers"
      actions={
        <div className="flex items-center gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept=".yaml,.yml"
            onChange={handleImportFile}
            className="hidden"
          />
          <Button size="sm" variant="outline" className="fusion-text-micro h-7" onClick={() => fileInputRef.current?.click()}>
            <Upload className="w-3 h-3 mr-1" />
            Import
          </Button>
          <Button size="sm" variant="outline" className="fusion-text-micro h-7" onClick={() => navigate({ to: '/dashboard/enrichers/new' as string })}>
            <PlusIcon className="w-3 h-3 mr-1" />
            Новый
          </Button>
        </div>
      }
    >
      {!isBannerDismissed && (
        <div className="mb-4 flex items-center gap-3 rounded-sm border border-[var(--fusion-ops-blue)]/30 bg-[color-mix(in_srgb,var(--fusion-ops-blue)_8%,transparent)] px-3 py-2">
          <FlaskConical className="h-4 w-4 shrink-0 text-[var(--fusion-ops-blue)]" />
          <p className="flex-1 fusion-text-micro text-[var(--fusion-ops-blue)]">
            Template enrichers — <strong>beta</strong>
          </p>
          <button
            onClick={() => setIsBannerDismissed(true)}
            className="shrink-0 rounded p-1"
            aria-label="Dismiss"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {isLoading ? (
        <SkeletonList rowCount={6} mode="card" />
      ) : error ? (
        <ErrorState
          title="Couldn't load templates"
          description="Something went wrong while fetching data. Please try again."
          error={error}
          onRetry={() => refetch()}
        />
      ) : !templates?.length ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <FileX className="w-8 h-8 text-[var(--fusion-text-tertiary)] mb-3" />
          <p className="fusion-text-data mb-4">Нет шаблонов</p>
          <Button onClick={() => navigate({ to: '/dashboard/enrichers/new' as string })}>
            <PlusIcon className="w-4 h-4 mr-2" />
            Создать шаблон
          </Button>
        </div>
      ) : (
        <Tabs defaultValue="All" className="space-y-4">
          <TabsList className="bg-[var(--fusion-bg-panel)] border border-[var(--fusion-border)]">
            {allCategories.map((category) => (
              <TabsTrigger key={category} value={category} className="fusion-text-micro">
                {category}
              </TabsTrigger>
            ))}
          </TabsList>

          {allCategories.map((category) => (
            <TabsContent key={category} value={category} className="mt-0">
              <div className="divide-y divide-[var(--fusion-border)] border border-[var(--fusion-border)] rounded-[var(--fusion-radius-sm)]">
                {templates
                  ?.filter((template) =>
                    category === 'All' ? true : template.category === category
                  )
                  .map((template) => (
                    <button
                      key={template.id}
                      type="button"
                      className="w-full flex items-center justify-between gap-3 px-3 py-2 text-left hover:bg-[var(--fusion-bg-interactive)]"
                      onClick={() => navigate({ to: `/dashboard/enrichers/${template.id}` })}
                    >
                      <div className="min-w-0">
                        <p className="fusion-text-data truncate">{template.name || '(Unnamed)'}</p>
                        <p className="fusion-text-micro truncate text-[var(--fusion-text-tertiary)]">
                          {template.description}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <Badge variant="outline" className="fusion-text-micro">v{template.version}</Badge>
                        <span className="fusion-text-micro text-[var(--fusion-text-tertiary)] inline-flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatDistanceToNow(new Date(template.updated_at || template.created_at), { addSuffix: true })}
                        </span>
                        <FileCode2 className="w-3.5 h-3.5 text-[var(--fusion-text-tertiary)]" />
                      </div>
                    </button>
                  ))}
              </div>
            </TabsContent>
          ))}
        </Tabs>
      )}
    </FusionPlatformShell>
  )
}
