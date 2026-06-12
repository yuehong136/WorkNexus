import { useMutation, useQueryClient } from '@tanstack/react-query'
import { revokeInvite } from '@worknexus/contracts'

import { unwrap } from '@/lib/api-client'
import { settingsKeys } from '@/features/settings/api/keys'

export function useRevokeInviteMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (inviteId: string) => unwrap(await revokeInvite(inviteId)),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: settingsKeys.all })
    },
  })
}
