import { useMutation, useQueryClient } from '@tanstack/react-query'
import { updateIntake, type IntakeUpdateIn } from '@worknexus/contracts'

import { intakeKeys } from '@/features/intake/api/keys'
import { unwrap } from '@/lib/api-client'

export function useUpdateIntakeMutation(projectId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ intakeId, body }: { intakeId: string; body: IntakeUpdateIn }) =>
      unwrap(await updateIntake(intakeId, body)),
    meta: { suppressToast: true },
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: intakeKeys.lists(projectId) })
      void queryClient.invalidateQueries({ queryKey: intakeKeys.detail(data.id) })
    },
  })
}
