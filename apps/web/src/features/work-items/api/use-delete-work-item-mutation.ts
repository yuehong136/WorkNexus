import { useMutation, useQueryClient } from '@tanstack/react-query'
import { deleteWorkItem } from '@worknexus/contracts'

import { workItemKeys } from '@/features/work-items/api/keys'

export function useDeleteWorkItemMutation(projectId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    // deleteWorkItem returns an empty envelope (data: null), so it is not unwrapped.
    mutationFn: async (workItemId: string) => {
      await deleteWorkItem(workItemId)
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: workItemKeys.lists(projectId) })
    },
  })
}
