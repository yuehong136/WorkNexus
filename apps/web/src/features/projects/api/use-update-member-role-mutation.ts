import { useMutation, useQueryClient } from '@tanstack/react-query'
import { updateProjectMember, type ProjectMemberUpdateIn } from '@worknexus/contracts'

import { projectKeys } from '@/features/projects/api/keys'
import { unwrap } from '@/lib/api-client'

interface UpdateMemberRoleVariables {
  projectId: string
  userId: string
  body: ProjectMemberUpdateIn
}

export function useUpdateMemberRoleMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ projectId, userId, body }: UpdateMemberRoleVariables) =>
      unwrap(await updateProjectMember(projectId, userId, body)),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: projectKeys.all })
    },
  })
}
