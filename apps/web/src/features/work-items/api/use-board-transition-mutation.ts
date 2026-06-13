import { useMutation, useQueryClient } from '@tanstack/react-query'
import { transitionWorkItem, type WorkItemStatus } from '@worknexus/contracts'

import { workItemKeys } from '@/features/work-items/api/keys'
import { unwrap } from '@/lib/api-client'

interface BoardTransitionVariables {
  workItemId: string
  status: WorkItemStatus
}

// Board drag moves any card, so the transition mutation is keyed by the project (not a
// single work item) and takes the work item id per call.
export function useBoardTransitionMutation(projectId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ workItemId, status }: BoardTransitionVariables) =>
      unwrap(await transitionWorkItem(workItemId, { status })),
    meta: { suppressToast: true },
    onSuccess: (_data, { workItemId }) => {
      void queryClient.invalidateQueries({ queryKey: workItemKeys.lists(projectId) })
      void queryClient.invalidateQueries({ queryKey: workItemKeys.detail(workItemId) })
      void queryClient.invalidateQueries({ queryKey: workItemKeys.activities(workItemId) })
    },
  })
}
