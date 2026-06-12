import { useQuery } from '@tanstack/react-query'
import { listInvites } from '@worknexus/contracts'

import { unwrap } from '@/lib/api-client'
import { settingsKeys, type PageQuery } from '@/features/settings/api/keys'

export function useInvitesQuery(params: PageQuery, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: settingsKeys.invites(params),
    queryFn: async () => unwrap(await listInvites({ page: params.page, page_size: params.pageSize })),
    enabled: options?.enabled,
  })
}
