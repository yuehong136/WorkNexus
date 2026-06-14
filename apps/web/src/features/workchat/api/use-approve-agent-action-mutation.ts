import { useMutation, useQueryClient } from '@tanstack/react-query'
import { approveAgentAction } from '@worknexus/contracts'

import { workchatKeys } from '@/features/workchat/api/keys'
import { unwrap } from '@/lib/api-client'

export function useApproveAgentActionMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (agentActionId: string) => unwrap(await approveAgentAction(agentActionId)),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: workchatKeys.agentActions() })
    },
  })
}
