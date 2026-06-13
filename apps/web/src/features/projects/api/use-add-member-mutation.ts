import { useMutation, useQueryClient } from '@tanstack/react-query'
import { addProjectMember, type ProjectMemberAddIn } from '@worknexus/contracts'

import { projectKeys } from '@/features/projects/api/keys'
import { unwrap } from '@/lib/api-client'

interface AddMemberVariables {
  projectId: string
  body: ProjectMemberAddIn
}

export function useAddMemberMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ projectId, body }: AddMemberVariables) => unwrap(await addProjectMember(projectId, body)),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: projectKeys.all })
    },
  })
}
