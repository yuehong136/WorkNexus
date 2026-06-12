import { useMutation, useQueryClient } from '@tanstack/react-query'
import { runSetup, type SetupIn } from '@worknexus/contracts'

import { unwrap } from '@/lib/api-client'
import { authKeys } from '@/lib/auth/keys'

export function useSetupMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: SetupIn) => unwrap(await runSetup(body)),
    meta: { suppressToast: true },
    onSuccess: (context) => {
      queryClient.setQueryData(authKeys.me(), context)
      void queryClient.invalidateQueries({ queryKey: authKeys.setupStatus() })
    },
  })
}
