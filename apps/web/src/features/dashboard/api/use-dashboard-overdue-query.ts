import { useQuery } from '@tanstack/react-query'
import { getDashboardOverdue, type GetDashboardOverdueParams } from '@worknexus/contracts'

import { dashboardKeys } from '@/features/dashboard/api/keys'
import { unwrap } from '@/lib/api-client'

export function useDashboardOverdueQuery(projectId: string, params: GetDashboardOverdueParams) {
  return useQuery({
    queryKey: dashboardKeys.overdue(projectId, params),
    queryFn: async () => unwrap(await getDashboardOverdue(projectId, params)),
    staleTime: 0,
  })
}
