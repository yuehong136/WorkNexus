import { useQuery } from '@tanstack/react-query'
import { getProjectSummary } from '@worknexus/contracts'

import { projectKeys } from '@/features/projects/api/keys'
import { unwrap } from '@/lib/api-client'

// The project overview surfaces work-item stats. The endpoint is owned by the
// work_items module, but the consumer is the projects overview page, so the query
// lives here (features cannot import each other).
export function useProjectSummaryQuery(projectId: string) {
  return useQuery({
    queryKey: projectKeys.summary(projectId),
    queryFn: async () => unwrap(await getProjectSummary(projectId)),
  })
}
