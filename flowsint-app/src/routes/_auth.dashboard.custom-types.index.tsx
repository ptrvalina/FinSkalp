import { createFileRoute } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { PlusIcon, Clock, FileX, Trash2, Edit } from 'lucide-react'
import { useNavigate } from '@tanstack/react-router'
import { formatDistanceToNow } from 'date-fns'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { customTypeService, CustomType } from '@/api/custom-type-service'
import ErrorState from '@/components/shared/error-state'
import { toast } from 'sonner'
import { useConfirm } from '@/components/use-confirm-dialog'
import { FusionPlatformShell, FusionEmptyState, FusionSkeleton } from '@/fusion'

export const Route = createFileRoute('/_auth/dashboard/custom-types/')({
  component: CustomTypesPage
})

const getStatusBadge = (status: string) => {
  const variants: Record<string, 'default' | 'secondary' | 'outline'> = {
    draft: 'outline',
    published: 'default',
    archived: 'secondary'
  }
  return (
    <Badge variant={variants[status] || 'default'} className="fusion-text-micro rounded-sm">
      {status}
    </Badge>
  )
}

function CustomTypesPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { confirm } = useConfirm()
  const {
    data: customTypes,
    isLoading,
    error,
    refetch
  } = useQuery<CustomType[]>({
    queryKey: ['custom-types'],
    queryFn: () => customTypeService.list()
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => customTypeService.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['custom-types'] })
      queryClient.invalidateQueries({ queryKey: ['actionItems'] })
      toast.success('Custom type deleted successfully')
    },
    onError: (error: Error) => {
      toast.error(`Failed to delete custom type: ${error.message}`)
    }
  })

  const handleDelete = async (customType: CustomType) => {
    if (await confirm({ title: "Are you sure you want to delete this custom type ?", message: "this action is irreversible." }))
      deleteMutation.mutate(customType.id)
  }

  const draftTypes = customTypes?.filter((t) => t.status === 'draft') || []
  const publishedTypes = customTypes?.filter((t) => t.status === 'published') || []
  const archivedTypes = customTypes?.filter((t) => t.status === 'archived') || []

  return (
    <FusionPlatformShell
      title="Архитектор схем"
      subtitle="Управляемые пользовательские типы данных"
      activeSection="types"
      actions={
        <Button
          size="sm"
          variant="outline"
          className="fusion-text-micro h-7"
          // @ts-ignore
          onClick={() => navigate({ to: '/dashboard/custom-types/new' })}
        >
          <PlusIcon className="w-3 h-3 mr-1" />
          Новая схема
        </Button>
      }
    >
      {isLoading ? (
        <FusionSkeleton rows={6} variant="row" />
      ) : error ? (
        <ErrorState
          title="Couldn't load custom types"
          description="Something went wrong while fetching data. Please try again."
          error={error}
          onRetry={() => refetch()}
        />
      ) : !customTypes?.length ? (
        <FusionEmptyState
          title="Нет пользовательских схем"
          description="Определите типы сущностей для графа расследования."
          icon={<FileX />}
          action={
            <Button onClick={() => navigate({ to: '/dashboard/custom-types/new' as string })}>
              <PlusIcon className="w-4 h-4 mr-2" />
              Создать схему
            </Button>
          }
        />
      ) : (
        <Tabs defaultValue="all" className="w-full">
          <TabsList className="bg-[var(--fusion-bg-panel)] border border-[var(--fusion-border)]">
            <TabsTrigger value="all" className="fusion-text-micro">Все ({customTypes.length})</TabsTrigger>
            <TabsTrigger value="published" className="fusion-text-micro">Published ({publishedTypes.length})</TabsTrigger>
            <TabsTrigger value="draft" className="fusion-text-micro">Drafts ({draftTypes.length})</TabsTrigger>
            <TabsTrigger value="archived" className="fusion-text-micro">Archived ({archivedTypes.length})</TabsTrigger>
          </TabsList>

          <TabsContent value="all" className="mt-4">
            <CustomTypesList types={customTypes} onDelete={handleDelete} navigate={navigate} />
          </TabsContent>
          <TabsContent value="published" className="mt-4">
            <CustomTypesList types={publishedTypes} onDelete={handleDelete} navigate={navigate} />
          </TabsContent>
          <TabsContent value="draft" className="mt-4">
            <CustomTypesList types={draftTypes} onDelete={handleDelete} navigate={navigate} />
          </TabsContent>
          <TabsContent value="archived" className="mt-4">
            <CustomTypesList types={archivedTypes} onDelete={handleDelete} navigate={navigate} />
          </TabsContent>
        </Tabs>
      )}
    </FusionPlatformShell>
  )
}

interface CustomTypesListProps {
  types: CustomType[]
  onDelete: (type: CustomType) => void
  navigate: any
}

function CustomTypesList({ types, onDelete, navigate }: CustomTypesListProps) {
  if (types.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <FileX className="w-8 h-8 text-[var(--fusion-text-tertiary)] mb-2" />
        <p className="fusion-text-micro">Пусто</p>
      </div>
    )
  }

  return (
    <div className="divide-y divide-[var(--fusion-border)] border border-[var(--fusion-border)] rounded-[var(--fusion-radius-sm)]">
      {types.map((customType) => (
        <div key={customType.id} className="flex items-center justify-between gap-3 px-3 py-2 hover:bg-[var(--fusion-bg-interactive)]">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <p className="fusion-text-data">{customType.name}</p>
              {getStatusBadge(customType.status)}
            </div>
            <p className="fusion-text-micro text-[var(--fusion-text-tertiary)] truncate">
              {customType.description || '—'}
            </p>
            <span className="fusion-text-micro inline-flex items-center gap-1 text-[var(--fusion-text-tertiary)] mt-0.5">
              <Clock className="w-3 h-3" />
              {formatDistanceToNow(new Date(customType.updated_at), { addSuffix: true })}
            </span>
          </div>
          <div className="flex items-center gap-1 shrink-0">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 fusion-text-micro"
              onClick={() => navigate({ to: `/dashboard/custom-types/${customType.id}` })}
            >
              <Edit className="w-3 h-3 mr-1" />
              Edit
            </Button>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => onDelete(customType)}>
              <Trash2 className="w-3.5 h-3.5 text-[var(--fusion-ops-red)]" />
            </Button>
          </div>
        </div>
      ))}
    </div>
  )
}
