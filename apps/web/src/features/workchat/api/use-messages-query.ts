import { useQuery } from '@tanstack/react-query'
import { listMessages } from '@worknexus/contracts'

import { workchatKeys } from '@/features/workchat/api/keys'
import { unwrap } from '@/lib/api-client'

const PAGE_SIZE = 50

export function useMessagesQuery(conversationId: string, enabled = true) {
  return useQuery({
    queryKey: workchatKeys.messages(conversationId),
    queryFn: async () => unwrap(await listMessages(conversationId, { page: 1, page_size: PAGE_SIZE })),
    enabled: enabled && conversationId !== '',
  })
}
