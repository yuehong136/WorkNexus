import { useMutation, useQueryClient } from '@tanstack/react-query'
import { updateWorkItem, type WorkItemUpdateIn } from '@worknexus/contracts'

import { workItemKeys } from '@/features/work-items/api/keys'
import { unwrap } from '@/lib/api-client'

export function useUpdateWorkItemMutation(projectId: string, workItemId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: WorkItemUpdateIn) => unwrap(await updateWorkItem(workItemId, body)),
    meta: { suppressToast: true },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: workItemKeys.detail(workItemId) })
      void queryClient.invalidateQueries({ queryKey: workItemKeys.lists(projectId) })
      void queryClient.invalidateQueries({ queryKey: workItemKeys.activities(workItemId) })
    },
  })
}
