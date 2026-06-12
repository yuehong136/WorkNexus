import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createInvite, type InviteCreateIn } from '@worknexus/contracts'

import { unwrap } from '@/lib/api-client'
import { settingsKeys } from '@/features/settings/api/keys'

export function useCreateInviteMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: InviteCreateIn) => unwrap(await createInvite(body)),
    meta: { suppressToast: true },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: settingsKeys.all })
    },
  })
}
