import type { ColumnDef } from '@tanstack/react-table'
import type { ProjectOut, ProjectStatus } from '@worknexus/contracts'
import { Link } from 'react-router'

import { Badge } from '@/components/ui/badge'
import { formatDateTime } from '@/lib/datetime'
import { paths } from '@/lib/paths'
import type { AppTFunction } from '@/locales/i18n'

const statusVariant: Record<ProjectStatus, 'success' | 'secondary'> = {
  active: 'success',
  archived: 'secondary',
}

export function projectColumns(t: AppTFunction): ColumnDef<ProjectOut, unknown>[] {
  return [
    {
      accessorKey: 'name',
      header: t('projects:columns.name'),
      cell: ({ row }) => (
        <Link to={paths.projectDetail(row.original.id)} className="font-medium text-text-primary hover:underline">
          {row.original.name}
        </Link>
      ),
    },
    {
      accessorKey: 'key',
      header: t('projects:columns.key'),
      cell: ({ row }) => <span className="text-text-secondary">{row.original.key}</span>,
    },
    {
      accessorKey: 'status',
      header: t('projects:columns.status'),
      cell: ({ row }) => (
        <Badge variant={statusVariant[row.original.status]}>{t(`projects:status.${row.original.status}`)}</Badge>
      ),
    },
    {
      accessorKey: 'memberCount',
      header: t('projects:columns.memberCount'),
      cell: ({ row }) => row.original.memberCount,
    },
    {
      accessorKey: 'createdAt',
      header: t('projects:columns.createdAt'),
      cell: ({ row }) => formatDateTime(row.original.createdAt),
    },
  ]
}
