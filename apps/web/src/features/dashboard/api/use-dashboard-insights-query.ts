import { useQuery } from '@tanstack/react-query'
import { getDashboardAiInsights } from '@worknexus/contracts'

import { dashboardKeys } from '@/features/dashboard/api/keys'
import { unwrap } from '@/lib/api-client'

export function useDashboardInsightsQuery(projectId: string) {
  return useQuery({
    queryKey: dashboardKeys.insights(projectId),
    queryFn: async () => unwrap(await getDashboardAiInsights(projectId)),
    staleTime: 0,
  })
}
