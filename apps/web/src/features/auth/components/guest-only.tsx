import { Navigate, Outlet, useLocation } from 'react-router'

import { ErrorState } from '@/components/patterns/error-state'
import { PageSkeleton } from '@/components/patterns/page-skeleton'
import { useMeQuery } from '@/lib/auth/use-me-query'
import { useSetupStatusQuery } from '@/lib/auth/use-setup-status-query'
import { paths } from '@/lib/paths'

export function GuestOnly() {
  const location = useLocation()
  const setupStatus = useSetupStatusQuery()
  const initialized = setupStatus.data?.initialized === true
  const me = useMeQuery({ enabled: initialized })
  const onSetupRoute = location.pathname === paths.setup()

  if (setupStatus.isPending || (initialized && me.isPending)) return <PageSkeleton />
  if (setupStatus.isError) return <ErrorState onRetry={() => void setupStatus.refetch()} />
  if (!initialized) return onSetupRoute ? <Outlet /> : <Navigate to={paths.setup()} replace />
  if (onSetupRoute) return <Navigate to={paths.login()} replace />
  if (me.data) {
    const from = (location.state as { from?: string } | null)?.from
    return <Navigate to={from ?? paths.home()} replace />
  }
  return <Outlet />
}
