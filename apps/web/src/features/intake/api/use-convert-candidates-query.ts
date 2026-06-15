import { useQuery } from '@tanstack/react-query'
import { listWorkItems } from '@worknexus/contracts'

import { unwrap } from '@/lib/api-client'

// The mark-duplicate picker needs the project's existing work items. Reuses the work_items
// REST endpoint directly via contracts (not the work-items feature) to respect feature isolation.
export function useConvertCandidatesQuery(projectId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['intake', 'work-item-candidates', projectId] as const,
    queryFn: async () => unwrap(await listWorkItems(projectId, { page: 1, page_size: 100 })),
    enabled: options?.enabled ?? true,
  })
}
