import { useQuery } from '@tanstack/react-query'
import { listSkillInvocations, type ListSkillInvocationsParams } from '@worknexus/contracts'

import { skillKeys } from '@/features/skills/api/keys'
import { unwrap } from '@/lib/api-client'

export function useSkillInvocationsQuery(params: ListSkillInvocationsParams) {
  return useQuery({
    queryKey: skillKeys.invocations(params),
    queryFn: async () => unwrap(await listSkillInvocations(params)),
  })
}
