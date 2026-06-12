import { Navigate, Outlet, useLocation } from 'react-router'

import { ErrorState } from '@/components/patterns/error-state'
import { PageSkeleton } from '@/components/patterns/page-skeleton'
import { useMeQuery } from '@/lib/auth/use-me-query'
import { useSetupStatusQuery } from '@/lib/auth/use-setup-status-query'
import { paths } from '@/lib/paths'

export function RequireAuth() {
  const location = useLocation()
  const setupStatus = useSetupStatusQuery()
  const initialized = setupStatus.data?.initialized === true
  const me = useMeQuery({ enabled: initialized })

  if (setupStatus.isPending || (initialized && me.isPending)) return <PageSkeleton />
  if (setupStatus.isError) return <ErrorState onRetry={() => void setupStatus.refetch()} />
  if (!initialized) return <Navigate to={paths.setup()} replace />
  if (!me.data) return <Navigate to={paths.login()} replace state={{ from: location.pathname }} />
  return <Outlet />
}
