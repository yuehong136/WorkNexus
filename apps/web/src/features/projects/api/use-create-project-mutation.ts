import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createProject, type ProjectCreateIn } from '@worknexus/contracts'

import { projectKeys } from '@/features/projects/api/keys'
import { unwrap } from '@/lib/api-client'
import { authKeys } from '@/lib/auth/keys'

export function useCreateProjectMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: ProjectCreateIn) => unwrap(await createProject(body)),
    meta: { suppressToast: true },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: projectKeys.all })
      // /me.projects is derived from projects, so refresh it (drives nav + project-scoped permissions).
      void queryClient.invalidateQueries({ queryKey: authKeys.me() })
    },
  })
}
