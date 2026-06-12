import { useQuery } from '@tanstack/react-query'
import { getMe } from '@worknexus/contracts'

import { unwrap } from '@/lib/api-client'
import { authKeys } from '@/lib/auth/keys'

export function useMeQuery(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: authKeys.me(),
    queryFn: async () => unwrap(await getMe()),
    staleTime: 5 * 60_000,
    retry: false,
    enabled: options?.enabled,
  })
}
