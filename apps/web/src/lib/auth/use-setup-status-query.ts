import { useQuery } from '@tanstack/react-query'
import { getSetupStatus } from '@worknexus/contracts'

import { unwrap } from '@/lib/api-client'
import { authKeys } from '@/lib/auth/keys'

export function useSetupStatusQuery() {
  return useQuery({
    queryKey: authKeys.setupStatus(),
    queryFn: async () => unwrap(await getSetupStatus()),
    staleTime: 60_000,
  })
}
