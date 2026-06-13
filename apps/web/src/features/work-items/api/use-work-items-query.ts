import { useQuery } from '@tanstack/react-query'
import { listWorkItems, type ListWorkItemsParams } from '@worknexus/contracts'

import { workItemKeys } from '@/features/work-items/api/keys'
import { unwrap } from '@/lib/api-client'

export function useWorkItemsQuery(projectId: string, params: ListWorkItemsParams) {
  return useQuery({
    queryKey: workItemKeys.list(projectId, params),
    queryFn: async () => unwrap(await listWorkItems(projectId, params)),
  })
}
