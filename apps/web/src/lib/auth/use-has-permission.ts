import type { Permission } from '@worknexus/contracts'

import { useMeQuery } from '@/lib/auth/use-me-query'

export function useHasPermission(permission: Permission, projectId?: string): boolean {
  const { data: me } = useMeQuery()
  if (!me) return false
  if (projectId !== undefined) {
    const project = me.projects.find((p) => p.id === projectId)
    return project?.permissions.includes(permission) ?? false
  }
  return me.permissions.includes(permission)
}
