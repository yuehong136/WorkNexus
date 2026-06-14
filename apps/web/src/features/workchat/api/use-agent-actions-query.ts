import { useQuery } from '@tanstack/react-query'
import { listAgentActions, type ListAgentActionsParams } from '@worknexus/contracts'

import { workchatKeys } from '@/features/workchat/api/keys'
import { unwrap } from '@/lib/api-client'

export function useAgentActionsQuery(params: ListAgentActionsParams) {
  return useQuery({
    queryKey: workchatKeys.agentActionList(params),
    queryFn: async () => unwrap(await listAgentActions(params)),
  })
}
