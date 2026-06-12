import { useMutation, useQueryClient } from '@tanstack/react-query'
import { login, type LoginIn } from '@worknexus/contracts'

import { unwrap } from '@/lib/api-client'
import { authKeys } from '@/lib/auth/keys'

export function useLoginMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: LoginIn) => unwrap(await login(body)),
    meta: { suppressToast: true },
    onSuccess: (context) => {
      queryClient.setQueryData(authKeys.me(), context)
    },
  })
}
