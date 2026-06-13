import { useQuery } from '@tanstack/react-query'
import { getProject } from '@worknexus/contracts'

import { projectKeys } from '@/features/projects/api/keys'
import { unwrap } from '@/lib/api-client'

export function useProjectQuery(projectId: string) {
  return useQuery({
    queryKey: projectKeys.detail(projectId),
    queryFn: async () => unwrap(await getProject(projectId)),
  })
}
