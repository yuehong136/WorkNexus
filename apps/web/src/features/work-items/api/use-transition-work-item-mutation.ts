import { useMutation, useQueryClient } from '@tanstack/react-query'
import { transitionWorkItem, type WorkItemTransitionIn } from '@worknexus/contracts'

import { workItemKeys } from '@/features/work-items/api/keys'
import { unwrap } from '@/lib/api-client'

export function useTransitionWorkItemMutation(projectId: string, workItemId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: WorkItemTransitionIn) => unwrap(await transitionWorkItem(workItemId, body)),
    meta: { suppressToast: true },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: workItemKeys.detail(workItemId) })
      void queryClient.invalidateQueries({ queryKey: workItemKeys.lists(projectId) })
      void queryClient.invalidateQueries({ queryKey: workItemKeys.activities(workItemId) })
    },
  })
}
