import { useQuery } from '@tanstack/react-query'
import { listUsers } from '@worknexus/contracts'

import { unwrap } from '@/lib/api-client'

// The add-member dialog needs the tenant user list to pick from. Feature slices
// can't import each other, so projects keeps its own thin users query.
export function useTenantUsersQuery(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['projects', 'tenant-users'] as const,
    queryFn: async () => unwrap(await listUsers({ page: 1, page_size: 100 })),
    enabled: options?.enabled,
  })
}
