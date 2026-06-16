import type { ListAuditLogsParams } from '@worknexus/contracts'

export const auditKeys = {
  all: ['audit'] as const,
  list: (params: ListAuditLogsParams) => [...auditKeys.all, 'list', params] as const,
}
