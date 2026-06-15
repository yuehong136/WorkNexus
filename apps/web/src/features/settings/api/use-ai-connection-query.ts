import { useQuery } from '@tanstack/react-query'
import { getAiConnection } from '@worknexus/contracts'

import { settingsKeys } from '@/features/settings/api/keys'
import { unwrap } from '@/lib/api-client'

export function useAiConnectionQuery(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: settingsKeys.aiConnection(),
    queryFn: async () => unwrap(await getAiConnection()),
    enabled: options?.enabled,
  })
}
