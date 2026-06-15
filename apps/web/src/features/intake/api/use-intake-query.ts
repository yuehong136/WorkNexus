import { useQuery } from '@tanstack/react-query'
import { getIntake } from '@worknexus/contracts'

import { intakeKeys } from '@/features/intake/api/keys'
import { unwrap } from '@/lib/api-client'

export function useIntakeQuery(intakeId: string | null) {
  return useQuery({
    queryKey: intakeKeys.detail(intakeId ?? ''),
    queryFn: async () => unwrap(await getIntake(intakeId as string)),
    enabled: intakeId !== null,
  })
}
