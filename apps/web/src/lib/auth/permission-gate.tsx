import type { Permission } from '@worknexus/contracts'
import type { ReactNode } from 'react'

import { useHasPermission } from '@/lib/auth/use-has-permission'

interface PermissionGateProps {
  permission: Permission
  projectId?: string
  fallback?: ReactNode
  children: ReactNode
}

export function PermissionGate({ permission, projectId, fallback = null, children }: PermissionGateProps) {
  const allowed = useHasPermission(permission, projectId)
  return allowed ? children : fallback
}
