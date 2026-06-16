import { useQuery } from '@tanstack/react-query'
import { getHome } from '@worknexus/contracts'

import { homeKeys } from '@/features/home/api/keys'
import { unwrap } from '@/lib/api-client'

export function useHomeQuery() {
  return useQuery({
    queryKey: homeKeys.snapshot(),
    queryFn: async () => unwrap(await getHome()),
    // Reflect freshly created / confirmed items promptly after returning to the workbench.
    staleTime: 0,
  })
}
