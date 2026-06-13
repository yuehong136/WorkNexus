import { useQuery } from '@tanstack/react-query'
import { listWorkItemComments } from '@worknexus/contracts'

import { workItemKeys } from '@/features/work-items/api/keys'
import { unwrap } from '@/lib/api-client'

export function useWorkItemCommentsQuery(workItemId: string | null) {
  return useQuery({
    queryKey: workItemKeys.comments(workItemId ?? ''),
    queryFn: async () => unwrap(await listWorkItemComments(workItemId as string)),
    enabled: workItemId !== null,
  })
}
