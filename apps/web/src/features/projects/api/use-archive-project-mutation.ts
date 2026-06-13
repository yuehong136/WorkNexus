import { useMutation, useQueryClient } from '@tanstack/react-query'
import { archiveProject } from '@worknexus/contracts'

import { projectKeys } from '@/features/projects/api/keys'
import { unwrap } from '@/lib/api-client'
import { authKeys } from '@/lib/auth/keys'

export function useArchiveProjectMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (projectId: string) => unwrap(await archiveProject(projectId)),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: projectKeys.all })
      // Archiving removes the project from /me.projects (active-only), so refresh it.
      void queryClient.invalidateQueries({ queryKey: authKeys.me() })
    },
  })
}
