import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { keyService } from '../api/key-service'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from '../components/ui/dialog'
import { Label } from '../components/ui/label'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '../components/ui/table'
import { Loader2, Plus, Trash2, KeyRound } from 'lucide-react'
import { toast } from 'sonner'
import { useConfirm } from '../components/use-confirm-dialog'
import Loader from '@/components/loader'
import { type Key as KeyType } from '@/types/key'
import { queryKeys } from '@/api/query-keys'
import ErrorState from '@/components/shared/error-state'
import { FusionPlatformShell } from '@/fusion'
export const Route = createFileRoute('/_auth/dashboard/vault')({
  component: VaultPage
})

function VaultPage() {
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false)
  const [keyName, setKeyName] = useState('')
  const [apiKey, setApiKey] = useState('')
  const queryClient = useQueryClient()
  const { confirm } = useConfirm()

  // Fetch keys
  const {
    data: keys = [],
    isLoading: keysLoading,
    error: keysError,
    refetch
  } = useQuery<KeyType[]>({
    queryKey: queryKeys.keys.list,
    queryFn: () => keyService.get()
  })

  // Create key mutation
  const createKeyMutation = useMutation({
    mutationFn: keyService.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.keys.list })
      setIsAddDialogOpen(false)
      setKeyName('')
      setApiKey('')
      toast.success('API key added successfully!')
    },
    onError: (error) => {
      toast.error('Failed to add API key. Please try again.')
      console.error('Error creating key:', error)
    }
  })

  // Delete key mutation
  const deleteKeyMutation = useMutation({
    mutationFn: keyService.deleteById,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.keys.list })
      toast.success('API key deleted successfully!')
    },
    onError: (error) => {
      toast.error('Failed to delete API key. Please try again.')
      console.error('Error deleting key:', error)
    }
  })

  const handleAddKey = () => {
    if (!keyName.trim() || !apiKey.trim()) {
      toast.error('Please enter both a name and an API key')
      return
    }
    createKeyMutation.mutate({ name: keyName.trim(), key: apiKey })
  }

  const handleDeleteKey = async (keyId: string, keyName: string) => {
    const confirmed = await confirm({
      title: 'Delete API Key',
      message: `Are you sure you want to delete the API key "${keyName}"? This action cannot be undone.`
    })

    if (confirmed) {
      deleteKeyMutation.mutate(keyId)
    }
  }

  return (
    <FusionPlatformShell
      title="Хранилище ключей"
      subtitle="Зашифрованные учётные данные провайдеров"
      activeSection="vault"
      actions={
        <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
          <DialogTrigger asChild>
            <Button size="sm" variant="outline" className="fusion-text-micro h-7">
              <Plus className="w-3 h-3 mr-1" />
              Добавить
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle>Add credential</DialogTitle>
              <DialogDescription>
                Add a provider secret with a custom name. Credentials are encrypted and stored securely.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="keyName">Key Name</Label>
                <Input
                  id="keyName"
                  placeholder="e.g., OpenAI, GitHub, Shodan..."
                  value={keyName}
                  onChange={(e) => setKeyName(e.target.value)}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="apiKey">API Key</Label>
                <Input
                  id="apiKey"
                  type="password"
                  placeholder="Enter your API key"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setIsAddDialogOpen(false)}
                disabled={createKeyMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                onClick={handleAddKey}
                disabled={createKeyMutation.isPending || !keyName.trim() || !apiKey.trim()}
              >
                {createKeyMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                Save credential
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      }
    >
      {keysLoading ? (
        <Loader />
      ) : keysError ? (
        <ErrorState
          title="Couldn't load keys"
          description="Something went wrong while fetching data. Please try again."
          error={keysError}
          onRetry={() => refetch()}
        />
      ) : keys.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 gap-4">
          <KeyRound className="w-10 h-10 text-[var(--fusion-text-tertiary)]" strokeWidth={1.5} />
          <p className="fusion-text-data text-center">Нет сохранённых ключей</p>
          <Button size="sm" onClick={() => setIsAddDialogOpen(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Добавить ключ
          </Button>
        </div>
      ) : (
        <div className="overflow-hidden border border-[var(--fusion-border)] rounded-[var(--fusion-radius-sm)]">
          <Table>
            <TableHeader>
              <TableRow className="border-[var(--fusion-border)] hover:bg-transparent">
                <TableHead className="fusion-text-micro py-2">Имя</TableHead>
                <TableHead className="fusion-text-micro py-2">Добавлен</TableHead>
                <TableHead className="fusion-text-micro py-2 text-right">Действия</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {keys.map((key: KeyType) => (
                <TableRow key={key.id} className="border-[var(--fusion-border)] hover:bg-[var(--fusion-bg-interactive)]">
                  <TableCell className="fusion-text-data py-2">{key.name}</TableCell>
                  <TableCell className="fusion-text-micro py-2 text-[var(--fusion-text-tertiary)]">
                    {new Date(key.created_at).toLocaleDateString('ru-RU')}
                  </TableCell>
                  <TableCell className="text-right py-2">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-[var(--fusion-ops-red)]"
                      onClick={() => handleDeleteKey(key.id, key.name)}
                      disabled={deleteKeyMutation.isPending}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </FusionPlatformShell>
  )
}

export default VaultPage
