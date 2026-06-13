import { useMutation, useQueryClient } from '@tanstack/react-query'
import { removeProjectMember } from '@worknexus/contracts'

import { projectKeys } from '@/features/projects/api/keys'

interface RemoveMemberVariables {
  projectId: string
  userId: string
}

export function useRemoveMemberMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    // removeProjectMember returns an empty envelope (data: null), so it is not unwrapped.
    mutationFn: async ({ projectId, userId }: RemoveMemberVariables) => {
      await removeProjectMember(projectId, userId)
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: projectKeys.all })
    },
  })
}
