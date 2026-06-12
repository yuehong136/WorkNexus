import { useMutation, useQueryClient } from '@tanstack/react-query'
import { acceptInvite, type AcceptInviteIn } from '@worknexus/contracts'

import { unwrap } from '@/lib/api-client'
import { authKeys } from '@/lib/auth/keys'

export function useAcceptInviteMutation(token: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: AcceptInviteIn) => unwrap(await acceptInvite(token, body)),
    meta: { suppressToast: true },
    onSuccess: (context) => {
      queryClient.setQueryData(authKeys.me(), context)
    },
  })
}
