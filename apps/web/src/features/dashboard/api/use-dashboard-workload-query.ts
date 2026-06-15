import { useQuery } from '@tanstack/react-query'
import { getDashboardWorkload } from '@worknexus/contracts'

import { dashboardKeys } from '@/features/dashboard/api/keys'
import { unwrap } from '@/lib/api-client'

export function useDashboardWorkloadQuery(projectId: string) {
  return useQuery({
    queryKey: dashboardKeys.workload(projectId),
    queryFn: async () => unwrap(await getDashboardWorkload(projectId)),
    staleTime: 0,
  })
}
