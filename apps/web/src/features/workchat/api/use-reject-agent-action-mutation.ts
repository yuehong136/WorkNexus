import { useMutation, useQueryClient } from '@tanstack/react-query'
import { rejectAgentAction } from '@worknexus/contracts'

import { workchatKeys } from '@/features/workchat/api/keys'
import { unwrap } from '@/lib/api-client'

export function useRejectAgentActionMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (vars: { agentActionId: string; reason?: string }) =>
      unwrap(await rejectAgentAction(vars.agentActionId, { reason: vars.reason ?? null })),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: workchatKeys.agentActions() })
    },
  })
}
