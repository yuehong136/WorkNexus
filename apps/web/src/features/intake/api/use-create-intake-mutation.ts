import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createIntake, type IntakeCreateIn } from '@worknexus/contracts'

import { intakeKeys } from '@/features/intake/api/keys'
import { unwrap } from '@/lib/api-client'

export function useCreateIntakeMutation(projectId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: IntakeCreateIn) => unwrap(await createIntake(projectId, body)),
    meta: { suppressToast: true },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: intakeKeys.lists(projectId) })
    },
  })
}
