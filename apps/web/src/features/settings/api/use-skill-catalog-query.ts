import { useQuery } from '@tanstack/react-query'
import { listSkills } from '@worknexus/contracts'

import { settingsKeys } from '@/features/settings/api/keys'
import { unwrap } from '@/lib/api-client'

// Settings re-queries the skill catalog itself (features must not import each other);
// it renders a read-only execution-policy view distinct from the /skills center.
export function useSkillCatalogQuery(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: settingsKeys.skillCatalog(),
    queryFn: async () => unwrap(await listSkills()),
    enabled: options?.enabled,
  })
}
