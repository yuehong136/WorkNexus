import { useQuery } from '@tanstack/react-query'
import { listProjectMembers } from '@worknexus/contracts'

import { unwrap } from '@/lib/api-client'

// The convert form needs the member list for the assignee picker. The endpoint is owned by
// projects; features cannot import each other, so this thin query lives in intake.
export function useProjectMembersQuery(projectId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['intake', 'project-members', projectId] as const,
    queryFn: async () => unwrap(await listProjectMembers(projectId)),
    enabled: options?.enabled ?? true,
  })
}
