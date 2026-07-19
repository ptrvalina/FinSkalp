import { Link } from '@tanstack/react-router'
import { useLogin } from '@/hooks/use-auth'
import { FormProvider, useForm } from 'react-hook-form'
import FormField from '@/components/shared/form-field'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/login')({
  component: Login
})

const loginSchema = z.object({
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(1, 'Password is required'),
  rememberMe: z.boolean().optional()
})

type LoginFormValues = z.infer<typeof loginSchema>

function Login() {
  const methods = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      username: '',
      password: '',
      rememberMe: false
    }
  })

  const login = useLogin()

  const onSubmit = async (data: LoginFormValues) => {
    try {
      await login.mutateAsync({
        username: data.username,
        password: data.password
      })
    } catch (error) {
      console.error('Login error:', error)
    }
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4 fusion-root"
      style={{ background: 'var(--fusion-bg-void, #0b141c)', color: 'rgba(255,255,255,0.92)' }}
    >
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div
            className="mx-auto mb-3 flex h-10 w-10 items-center justify-center border text-xs font-bold"
            style={{ borderColor: '#2d363e', color: '#4a8fd4', fontFamily: 'JetBrains Mono, monospace' }}
          >
            ФС
          </div>
          <h1 className="text-lg font-semibold tracking-tight">FinSkalp Graph OS</h1>
          <p className="mt-1 text-xs" style={{ color: 'rgba(255,255,255,0.45)' }}>
            Secure gateway · финансовая разведка
          </p>
        </div>

        <div
          className="border p-6"
          style={{ background: '#182028', borderColor: '#2d363e', borderRadius: '2px' }}
        >
          <FormProvider {...methods}>
            <form className="space-y-4" onSubmit={methods.handleSubmit(onSubmit)}>
              {login.error && (
                <div
                  className="p-2 text-xs"
                  style={{
                    border: '1px solid color-mix(in srgb, #D64545 40%, transparent)',
                    background: 'color-mix(in srgb, #D64545 10%, transparent)',
                    color: '#D64545',
                  }}
                >
                  {login.error instanceof Error ? login.error.message : 'Login error'}
                </div>
              )}

              <FormField
                name="username"
                label="Email"
                placeholder="analyst@example.com"
                disabled={login.isPending}
              />

              <FormField
                name="password"
                label="Password"
                type="password"
                placeholder="••••••••"
                disabled={login.isPending}
              />

              <button
                type="submit"
                disabled={login.isPending || methods.formState.isSubmitting}
                className="w-full py-2 text-xs font-medium uppercase tracking-wider"
                style={{
                  background: '#4A8FD4',
                  color: '#0B1118',
                  border: 'none',
                  borderRadius: '2px',
                }}
              >
                {login.isPending || methods.formState.isSubmitting ? 'Вход…' : 'Войти'}
              </button>
            </form>
          </FormProvider>

          <p className="mt-4 text-center text-xs" style={{ color: 'rgba(255,255,255,0.45)' }}>
            Нет аккаунта?{' '}
            <Link to="/register" style={{ color: '#4A8FD4' }}>
              Регистрация
            </Link>
          </p>
        </div>

        <p
          className="mt-6 text-center font-mono text-[9px] uppercase tracking-[0.2em]"
          style={{ color: 'rgba(255,255,255,0.3)' }}
        >
          Constitution v3 · void #0b141c
        </p>
      </div>
    </div>
  )
}

export default Login
