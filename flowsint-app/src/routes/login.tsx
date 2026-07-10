import { Link } from '@tanstack/react-router'
import { useLogin } from '@/hooks/use-auth'
import { FormProvider, useForm } from 'react-hook-form'
import FormField from '@/components/shared/form-field'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { createFileRoute } from '@tanstack/react-router'
import { Badge } from '@/components/ui/badge'

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
  // Initialize React Hook Form
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
    <div className="min-h-screen bg-[var(--fs-bg-primary)] px-4 py-10 text-[var(--fs-text-primary)]">
      <div className="mx-auto grid max-w-6xl gap-8 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="rounded-lg border border-[var(--fs-border)] bg-[var(--fs-surface)] p-8 lg:p-10">
          <Badge className="rounded-sm border border-[var(--fs-border)] bg-transparent text-[var(--fs-accent)]">
            secure-gateway
          </Badge>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight">Secure Gateway</h1>
          <p className="mt-3 max-w-2xl text-sm text-[var(--fs-text-secondary)]">
            Self-hosted access to the FinSkalp investigation workspace, compliance lifecycle, vault,
            and forensic modules. Every analyst session is isolated, auditable, and bound to local
            infrastructure.
          </p>
          <div className="mt-8 grid gap-4 md:grid-cols-3">
            {[
              ['Environment', 'Self-hosted'],
              ['Controls', 'RBAC + audit'],
              ['Connectors', 'Sovereign gateway'],
            ].map(([label, value]) => (
              <div
                key={label}
                className="rounded-md border border-[var(--fs-border)] bg-[var(--fs-bg-secondary)] p-4"
              >
                <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--fs-text-tertiary)]">
                  {label}
                </p>
                <p className="mt-2 font-mono text-sm text-[var(--fs-text-primary)]">{value}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-[var(--fs-border)] bg-[var(--fs-surface-raised)] p-8">
          <div className="mb-6">
            <h2 className="text-2xl font-semibold">Analyst Sign In</h2>
            <p className="mt-2 text-sm text-[var(--fs-text-secondary)]">
              Use your workspace credentials to continue to the investigation environment.
            </p>
          </div>

        <FormProvider {...methods}>
            <form className="space-y-6" onSubmit={methods.handleSubmit(onSubmit)}>
            {/* Display login error */}
            {login.error && (
                <div className="mb-4 rounded-sm border border-[var(--fs-risk-critical)]/40 bg-[color-mix(in_srgb,var(--fs-risk-critical)_12%,transparent)] p-3 text-sm text-[var(--fs-risk-critical)]">
                {login.error instanceof Error ? login.error.message : 'Login error'}
              </div>
            )}

              <div className="space-y-4 rounded-md">
              {/* Username field */}
              <FormField
                name="username"
                  label="Email"
                  placeholder="analyst@finskalp.local"
                disabled={login.isPending}
              />

              {/* Password field */}
              <FormField
                name="password"
                label="Password"
                type="password"
                  placeholder="Workspace password"
                disabled={login.isPending}
              />
            </div>

            {/* Submit button */}
            <div>
              <button
                type="submit"
                disabled={login.isPending || methods.formState.isSubmitting}
                  className="group relative flex w-full justify-center rounded-sm border border-transparent bg-[var(--fs-accent)] px-4 py-2.5 text-sm font-medium text-[var(--bg-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--fs-accent)] focus:ring-offset-2 focus:ring-offset-[var(--fs-surface-raised)]"
              >
                {login.isPending || methods.formState.isSubmitting ? (
                  <span className="flex items-center">
                    <svg
                      className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      ></circle>
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                    Signing in...
                  </span>
                  ) : (
                    'Enter workspace'
                  )}
              </button>
            </div>
          </form>
        </FormProvider>

        {/* Link to registration */}
          <div className="mt-6 text-center">
            <p className="text-sm text-[var(--fs-text-secondary)]">
            Don't have an account?{' '}
              <Link to="/register" className="font-medium text-[var(--fs-accent)]">
              Create an account
            </Link>
          </p>
        </div>
        </div>
      </div>
    </div>
  )
}

export default Login
