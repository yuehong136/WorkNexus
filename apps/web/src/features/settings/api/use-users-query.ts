import { useQuery } from '@tanstack/react-query'
import { listUsers } from '@worknexus/contracts'

import { unwrap } from '@/lib/api-client'
import { settingsKeys, type PageQuery } from '@/features/settings/api/keys'

export function useUsersQuery(params: PageQuery) {
  return useQuery({
    queryKey: settingsKeys.users(params),
    queryFn: async () => unwrap(await listUsers({ page: params.page, page_size: params.pageSize })),
  })
}
