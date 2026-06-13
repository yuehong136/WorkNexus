import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createWorkItemRelation, type RelationCreateIn } from '@worknexus/contracts'

import { workItemKeys } from '@/features/work-items/api/keys'
import { unwrap } from '@/lib/api-client'

export function useCreateRelationMutation(workItemId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: RelationCreateIn) => unwrap(await createWorkItemRelation(workItemId, body)),
    meta: { suppressToast: true },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: workItemKeys.relations(workItemId) })
      void queryClient.invalidateQueries({ queryKey: workItemKeys.activities(workItemId) })
    },
  })
}
