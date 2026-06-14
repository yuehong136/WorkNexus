import { useQuery } from '@tanstack/react-query'
import { getSkillInvocation } from '@worknexus/contracts'

import { skillKeys } from '@/features/skills/api/keys'
import { unwrap } from '@/lib/api-client'

export function useSkillInvocationQuery(invocationId: string | null) {
  return useQuery({
    queryKey: skillKeys.invocationDetail(invocationId ?? ''),
    queryFn: async () => unwrap(await getSkillInvocation(invocationId as string)),
    enabled: invocationId !== null,
  })
}
