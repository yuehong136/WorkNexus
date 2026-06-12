import { useQuery } from '@tanstack/react-query'
import { getInvite } from '@worknexus/contracts'

import { unwrap } from '@/lib/api-client'
import { authKeys } from '@/lib/auth/keys'

export function useInvitePreviewQuery(token: string) {
  return useQuery({
    queryKey: authKeys.invitePreview(token),
    queryFn: async () => unwrap(await getInvite(token)),
    retry: false,
  })
}
