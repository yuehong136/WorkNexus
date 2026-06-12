import type { ColumnDef } from '@tanstack/react-table'
import type { InviteOut, UserListOut } from '@worknexus/contracts'

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { formatDateTime } from '@/lib/datetime'
import type { AppTFunction } from '@/locales/i18n'

const userStatusVariant = {
  active: 'success',
  invited: 'secondary',
  disabled: 'error',
} as const

export function userColumns(t: AppTFunction): ColumnDef<UserListOut, unknown>[] {
  return [
    {
      accessorKey: 'displayName',
      header: t('settings:members.columns.name'),
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Avatar className="size-7">
            {row.original.avatarUrl ? (
              <AvatarImage src={row.original.avatarUrl} alt={row.original.displayName} />
            ) : null}
            <AvatarFallback>{row.original.displayName.slice(0, 2)}</AvatarFallback>
          </Avatar>
          <span className="font-medium">{row.original.displayName}</span>
        </div>
      ),
    },
    { accessorKey: 'email', header: t('settings:members.columns.email') },
    {
      accessorKey: 'status',
      header: t('settings:members.columns.status'),
      cell: ({ row }) => (
        <Badge variant={userStatusVariant[row.original.status]}>
          {t(`settings:members.userStatus.${row.original.status}`)}
        </Badge>
      ),
    },
    {
      accessorKey: 'lastLoginAt',
      header: t('settings:members.columns.lastLoginAt'),
      cell: ({ row }) => formatDateTime(row.original.lastLoginAt),
    },
    {
      accessorKey: 'createdAt',
      header: t('settings:members.columns.createdAt'),
      cell: ({ row }) => formatDateTime(row.original.createdAt),
    },
  ]
}

const inviteStatusVariant = {
  pending: 'secondary',
  accepted: 'success',
  expired: 'warning',
  revoked: 'error',
} as const

export function inviteColumns(
  t: AppTFunction,
  renderActions: (invite: InviteOut) => React.ReactNode,
): ColumnDef<InviteOut, unknown>[] {
  return [
    { accessorKey: 'email', header: t('settings:members.columns.email') },
    {
      id: 'target',
      header: t('settings:members.columns.target'),
      cell: ({ row }) =>
        row.original.tenantRole
          ? t('settings:invite.targetTenantAdmin')
          : t(`settings:invite.roles.${row.original.projectRole ?? 'member'}`),
    },
    {
      accessorKey: 'status',
      header: t('settings:members.columns.status'),
      cell: ({ row }) => (
        <Badge variant={inviteStatusVariant[row.original.status]}>
          {t(`settings:members.inviteStatus.${row.original.status}`)}
        </Badge>
      ),
    },
    {
      accessorKey: 'expiresAt',
      header: t('settings:members.columns.expiresAt'),
      cell: ({ row }) => formatDateTime(row.original.expiresAt),
    },
    {
      id: 'actions',
      header: t('settings:members.columns.actions'),
      cell: ({ row }) => renderActions(row.original),
    },
  ]
}
