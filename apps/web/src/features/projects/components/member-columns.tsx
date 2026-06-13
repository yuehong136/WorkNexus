import type { ColumnDef } from '@tanstack/react-table'
import type { ProjectMemberOut, ProjectMemberRole } from '@worknexus/contracts'

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { formatDateTime } from '@/lib/datetime'
import { cn } from '@/lib/utils'
import type { AppTFunction } from '@/locales/i18n'

const selectClassName =
  'h-8 rounded-md border border-border-default bg-surface-primary px-2 text-sm text-text-primary focus-visible:border-border-strong focus-visible:outline-none disabled:opacity-60'

const ROLES: ProjectMemberRole[] = ['project_admin', 'member', 'viewer']

interface MemberColumnsOptions {
  canManage: boolean
  pending: boolean
  onRoleChange: (member: ProjectMemberOut, role: ProjectMemberRole) => void
  onRemove: (member: ProjectMemberOut) => void
}

export function memberColumns(
  t: AppTFunction,
  { canManage, pending, onRoleChange, onRemove }: MemberColumnsOptions,
): ColumnDef<ProjectMemberOut, unknown>[] {
  const columns: ColumnDef<ProjectMemberOut, unknown>[] = [
    {
      accessorKey: 'displayName',
      header: t('projects:members.columns.name'),
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
    { accessorKey: 'email', header: t('projects:members.columns.email') },
    {
      accessorKey: 'role',
      header: t('projects:members.columns.role'),
      cell: ({ row }) =>
        canManage ? (
          <select
            className={cn(selectClassName)}
            value={row.original.role}
            disabled={pending}
            aria-label={t('projects:members.role')}
            onChange={(event) => onRoleChange(row.original, event.target.value as ProjectMemberRole)}
          >
            {ROLES.map((role) => (
              <option key={role} value={role}>
                {t(`projects:roles.${role}`)}
              </option>
            ))}
          </select>
        ) : (
          t(`projects:roles.${row.original.role}`)
        ),
    },
    {
      accessorKey: 'createdAt',
      header: t('projects:members.columns.joinedAt'),
      cell: ({ row }) => formatDateTime(row.original.createdAt),
    },
  ]

  if (canManage) {
    columns.push({
      id: 'actions',
      header: t('projects:members.columns.actions'),
      cell: ({ row }) => (
        <Button variant="ghost" size="sm" disabled={pending} onClick={() => onRemove(row.original)}>
          {t('projects:members.remove')}
        </Button>
      ),
    })
  }

  return columns
}
