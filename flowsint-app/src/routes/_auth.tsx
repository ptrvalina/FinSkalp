import { Link, Outlet, createFileRoute } from '@tanstack/react-router'

import { requireAuth } from '@/lib/auth-utils'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertTriangle, Home } from 'lucide-react'

export const Route = createFileRoute('/_auth')({
  beforeLoad: ({ location }) => {
    requireAuth(location.href)
  },
  component: AuthLayout,
  errorComponent: ErrorComponent
})

function AuthLayout() {
  return <Outlet />
}

function ErrorComponent({ error }: { error: Error }) {
  const isDev = import.meta.env.DEV
  const message = error instanceof Error ? error.message : String(error)
  const stack = error instanceof Error ? error.stack : undefined

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-background">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
            <AlertTriangle className="h-6 w-6 text-destructive" />
          </div>
          <CardTitle className="text-xl">Something went wrong</CardTitle>
          <CardDescription>
            We encountered an unexpected error. Please try again or navigate to a safe location.
          </CardDescription>
          {isDev && message ? (
            <pre className="mt-4 max-h-48 overflow-auto rounded border border-destructive/30 bg-destructive/5 p-3 text-left text-xs text-destructive whitespace-pre-wrap">
              {message}
              {stack ? `\n\n${stack}` : ''}
            </pre>
          ) : null}
        </CardHeader>

        <CardFooter className="flex flex-col gap-2">
          <Link to="/dashboard">
            <Button className="flex-1">
              <Home className="mr-2 h-4 w-4" />
              Go to Dashboard
            </Button>
          </Link>
        </CardFooter>
      </Card>
    </div>
  )
}
