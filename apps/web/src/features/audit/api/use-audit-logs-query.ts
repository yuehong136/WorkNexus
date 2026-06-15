import { useQuery } from '@tanstack/react-query'
import { listAuditLogs, type ListAuditLogsParams } from '@worknexus/contracts'

import { auditKeys } from '@/features/audit/api/keys'
import { unwrap } from '@/lib/api-client'

export function useAuditLogsQuery(params: ListAuditLogsParams) {
  return useQuery({
    queryKey: auditKeys.list(params),
    queryFn: async () => unwrap(await listAuditLogs(params)),
  })
}
