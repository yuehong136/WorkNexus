import { useQuery } from '@tanstack/react-query'
import { listIntake, type ListIntakeParams } from '@worknexus/contracts'

import { intakeKeys } from '@/features/intake/api/keys'
import { unwrap } from '@/lib/api-client'

export function useIntakeListQuery(projectId: string, params: ListIntakeParams) {
  return useQuery({
    queryKey: intakeKeys.list(projectId, params),
    queryFn: async () => unwrap(await listIntake(projectId, params)),
  })
}
