import { useQuery } from '@tanstack/react-query'
import { listProjectMembers } from '@worknexus/contracts'

import { unwrap } from '@/lib/api-client'

// Work items need the project member list for the assignee picker/filter. The endpoint
// is owned by projects, but features cannot import each other, so this thin query lives here.
export function useProjectMembersQuery(projectId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['workItems', 'project-members', projectId] as const,
    queryFn: async () => unwrap(await listProjectMembers(projectId)),
    enabled: options?.enabled ?? true,
  })
}
