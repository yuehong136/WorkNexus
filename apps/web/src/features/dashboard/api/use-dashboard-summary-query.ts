import { useQuery } from '@tanstack/react-query'
import { getDashboardSummary } from '@worknexus/contracts'

import { dashboardKeys } from '@/features/dashboard/api/keys'
import { unwrap } from '@/lib/api-client'

export function useDashboardSummaryQuery(projectId: string) {
  return useQuery({
    queryKey: dashboardKeys.summary(projectId),
    queryFn: async () => unwrap(await getDashboardSummary(projectId)),
    // The dashboard is a live view: reflect work-item/intake changes on each open
    // (acceptance §12 step 16). Cross-feature mutations can't invalidate these keys.
    staleTime: 0,
  })
}
