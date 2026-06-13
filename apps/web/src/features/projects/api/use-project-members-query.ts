import { useQuery } from '@tanstack/react-query'
import { listProjectMembers } from '@worknexus/contracts'

import { projectKeys } from '@/features/projects/api/keys'
import { unwrap } from '@/lib/api-client'

export function useProjectMembersQuery(projectId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: projectKeys.members(projectId),
    queryFn: async () => unwrap(await listProjectMembers(projectId)),
    enabled: options?.enabled,
  })
}
