import { useQuery } from '@tanstack/react-query'
import { listWorkItemActivities } from '@worknexus/contracts'

import { workItemKeys } from '@/features/work-items/api/keys'
import { unwrap } from '@/lib/api-client'

export function useWorkItemActivitiesQuery(workItemId: string | null) {
  return useQuery({
    queryKey: workItemKeys.activities(workItemId ?? ''),
    queryFn: async () => unwrap(await listWorkItemActivities(workItemId as string)),
    enabled: workItemId !== null,
  })
}
