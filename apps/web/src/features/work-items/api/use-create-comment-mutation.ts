import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createWorkItemComment, type CommentCreateIn } from '@worknexus/contracts'

import { workItemKeys } from '@/features/work-items/api/keys'
import { unwrap } from '@/lib/api-client'

export function useCreateCommentMutation(workItemId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: CommentCreateIn) => unwrap(await createWorkItemComment(workItemId, body)),
    meta: { suppressToast: true },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: workItemKeys.comments(workItemId) })
      void queryClient.invalidateQueries({ queryKey: workItemKeys.activities(workItemId) })
    },
  })
}
