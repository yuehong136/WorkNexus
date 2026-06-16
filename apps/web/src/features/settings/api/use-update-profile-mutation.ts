import { useMutation, useQueryClient } from '@tanstack/react-query'
import { updateMe, type ProfileUpdateIn } from '@worknexus/contracts'

import { unwrap } from '@/lib/api-client'
import { authKeys } from '@/lib/auth/keys'

export function useUpdateProfileMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: ProfileUpdateIn) => unwrap(await updateMe(body)),
    onSuccess: (context) => {
      queryClient.setQueryData(authKeys.me(), context)
      void queryClient.invalidateQueries({ queryKey: authKeys.me() })
    },
  })
}
