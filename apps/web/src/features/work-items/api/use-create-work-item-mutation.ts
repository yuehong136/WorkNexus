import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createWorkItem, type WorkItemCreateIn } from '@worknexus/contracts'

import { workItemKeys } from '@/features/work-items/api/keys'
import { unwrap } from '@/lib/api-client'

export function useCreateWorkItemMutation(projectId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: WorkItemCreateIn) => unwrap(await createWorkItem(projectId, body)),
    meta: { suppressToast: true },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: workItemKeys.lists(projectId) })
    },
  })
}
