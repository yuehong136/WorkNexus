import { useMutation, useQueryClient } from '@tanstack/react-query'
import { updateProject, type ProjectUpdateIn } from '@worknexus/contracts'

import { projectKeys } from '@/features/projects/api/keys'
import { unwrap } from '@/lib/api-client'
import { authKeys } from '@/lib/auth/keys'

interface UpdateProjectVariables {
  projectId: string
  body: ProjectUpdateIn
}

export function useUpdateProjectMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ projectId, body }: UpdateProjectVariables) => unwrap(await updateProject(projectId, body)),
    meta: { suppressToast: true },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: projectKeys.all })
      // The project name shows in /me.projects (nav/switcher), so refresh it too.
      void queryClient.invalidateQueries({ queryKey: authKeys.me() })
    },
  })
}
