import { createFileRoute } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { authService } from '@/api/auth-service'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { UserAvatar } from '@/components/ui/avatar'
import { toast } from 'sonner'
import { useAuthStore } from '@/stores/auth-store'
import { getDisplayName } from '@/lib/user-display'
import { SESSION_QUERY_KEY } from '@/hooks/use-auth'
import { FusionPlatformShell } from '@/fusion'

export const Route = createFileRoute('/_auth/dashboard/profile')({
  component: ProfilePage,
})

function ProfilePage() {
  const authUser = useAuthStore((s) => s.user)
  const setAuth = useAuthStore((s) => s.setAuth)
  const token = useAuthStore((s) => s.token)

  const { data: profile, isLoading } = useQuery({
    queryKey: ['profile', 'me'],
    queryFn: authService.getCurrentUser,
  })

  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    avatar_url: '',
  })

  useEffect(() => {
    if (profile) {
      setForm({
        first_name: profile.first_name ?? '',
        last_name: profile.last_name ?? '',
        avatar_url: profile.avatar_url ?? '',
      })
    }
  }, [profile])

  const queryClient = useQueryClient()

  const updateMutation = useMutation({
    mutationFn: authService.updateProfile,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['profile', 'me'] })
      queryClient.invalidateQueries({ queryKey: SESSION_QUERY_KEY })
      if (token && authUser) {
        setAuth(token, {
          ...authUser,
          first_name: data.first_name ?? undefined,
          last_name: data.last_name ?? undefined,
          avatar_url: data.avatar_url ?? undefined,
          username: [data.first_name, data.last_name].filter(Boolean).join(' ') || authUser.email,
        })
      }
      toast.success('Profile updated')
    },
    onError: () => toast.error('Failed to update profile'),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    updateMutation.mutate(form)
  }

  const handleChange = (field: string, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  if (isLoading) {
    return (
      <FusionPlatformShell title="Профиль оператора" activeSection="profile">
        <div className="flex items-center justify-center py-16">
          <div className="w-6 h-6 border-2 border-[var(--fusion-ops-blue)] border-t-transparent rounded-full animate-spin" />
        </div>
      </FusionPlatformShell>
    )
  }

  const displayName = getDisplayName(profile)

  return (
    <FusionPlatformShell
      title="Профиль оператора"
      subtitle="Идентификация аналитика в рабочем пространстве"
      activeSection="profile"
    >
      <div className="max-w-lg space-y-6">

        {/* Avatar preview */}
        <div className="flex items-center gap-4">
          <UserAvatar
            user={{ ...profile, avatar_url: form.avatar_url || undefined }}
            size="xl"
            className="size-16 text-lg"
          />
          <div>
            <p className="font-medium">{displayName}</p>
            <p className="text-sm text-muted-foreground">{profile?.email}</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="first_name">First name</Label>
              <Input
                id="first_name"
                value={form.first_name}
                onChange={(e) => handleChange('first_name', e.target.value)}
                placeholder="John"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="last_name">Last name</Label>
              <Input
                id="last_name"
                value={form.last_name}
                onChange={(e) => handleChange('last_name', e.target.value)}
                placeholder="Doe"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="avatar_url">Avatar URL</Label>
            <Input
              id="avatar_url"
              value={form.avatar_url}
              onChange={(e) => handleChange('avatar_url', e.target.value)}
              placeholder="https://..."
            />
          </div>

          <div className="space-y-2">
            <Label>Email</Label>
            <Input value={profile?.email ?? ''} disabled className="opacity-60" />
          </div>

          <div className="pt-2">
            <Button type="submit" disabled={updateMutation.isPending}>
              {updateMutation.isPending ? 'Saving...' : 'Save changes'}
            </Button>
          </div>
        </form>
      </div>
    </FusionPlatformShell>
  )
}
