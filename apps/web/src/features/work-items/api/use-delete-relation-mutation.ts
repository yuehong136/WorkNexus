import { useMutation, useQueryClient } from '@tanstack/react-query'
import { deleteWorkItemRelation } from '@worknexus/contracts'

import { workItemKeys } from '@/features/work-items/api/keys'

export function useDeleteRelationMutation(workItemId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    // deleteWorkItemRelation returns an empty envelope (data: null), so it is not unwrapped.
    mutationFn: async (relationId: string) => {
      await deleteWorkItemRelation(workItemId, relationId)
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: workItemKeys.relations(workItemId) })
      void queryClient.invalidateQueries({ queryKey: workItemKeys.activities(workItemId) })
    },
  })
}
