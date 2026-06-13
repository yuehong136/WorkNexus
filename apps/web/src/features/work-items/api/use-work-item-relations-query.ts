import { useQuery } from '@tanstack/react-query'
import { listWorkItemRelations } from '@worknexus/contracts'

import { workItemKeys } from '@/features/work-items/api/keys'
import { unwrap } from '@/lib/api-client'

export function useWorkItemRelationsQuery(workItemId: string | null) {
  return useQuery({
    queryKey: workItemKeys.relations(workItemId ?? ''),
    queryFn: async () => unwrap(await listWorkItemRelations(workItemId as string)),
    enabled: workItemId !== null,
  })
}
