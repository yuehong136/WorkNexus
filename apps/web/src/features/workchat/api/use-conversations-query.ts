import { useQuery } from '@tanstack/react-query'
import { listConversations } from '@worknexus/contracts'

import { workchatKeys } from '@/features/workchat/api/keys'
import { unwrap } from '@/lib/api-client'

export function useConversationsQuery(projectId: string) {
  return useQuery({
    queryKey: workchatKeys.conversations(projectId),
    queryFn: async () => unwrap(await listConversations(projectId)),
  })
}
