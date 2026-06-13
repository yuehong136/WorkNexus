import { useQuery } from '@tanstack/react-query'
import { getWorkItem } from '@worknexus/contracts'

import { workItemKeys } from '@/features/work-items/api/keys'
import { unwrap } from '@/lib/api-client'

export function useWorkItemQuery(workItemId: string | null) {
  return useQuery({
    queryKey: workItemKeys.detail(workItemId ?? ''),
    queryFn: async () => unwrap(await getWorkItem(workItemId as string)),
    enabled: workItemId !== null,
  })
}
