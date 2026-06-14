import { useQuery } from '@tanstack/react-query'
import { listSkills } from '@worknexus/contracts'

import { skillKeys } from '@/features/skills/api/keys'
import { unwrap } from '@/lib/api-client'

export function useSkillsQuery() {
  return useQuery({
    queryKey: skillKeys.catalog(),
    queryFn: async () => unwrap(await listSkills()),
  })
}
