import { useQuery } from '@tanstack/react-query'
import { listProjects } from '@worknexus/contracts'

import { projectKeys, type ProjectsListQuery } from '@/features/projects/api/keys'
import { unwrap } from '@/lib/api-client'

export function useProjectsListQuery(params: ProjectsListQuery) {
  return useQuery({
    queryKey: projectKeys.list(params),
    queryFn: async () =>
      unwrap(await listProjects({ status: params.status, page: params.page, page_size: params.pageSize })),
  })
}
