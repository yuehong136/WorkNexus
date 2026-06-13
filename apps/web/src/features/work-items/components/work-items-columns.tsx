import type { ColumnDef } from '@tanstack/react-table'
import type { WorkItemOut, WorkItemPriority, WorkItemStatus } from '@worknexus/contracts'

import { Badge } from '@/components/ui/badge'
import { formatDateTime } from '@/lib/datetime'
import type { AppTFunction } from '@/locales/i18n'

type BadgeVariant = 'default' | 'secondary' | 'outline' | 'success' | 'warning' | 'error'

const statusVariant: Record<WorkItemStatus, BadgeVariant> = {
  backlog: 'secondary',
  todo: 'outline',
  in_progress: 'default',
  review: 'warning',
  done: 'success',
  cancelled: 'secondary',
}

const priorityVariant: Record<WorkItemPriority, BadgeVariant> = {
  low: 'secondary',
  medium: 'outline',
  high: 'warning',
  urgent: 'error',
}

export function workItemColumns(t: AppTFunction): ColumnDef<WorkItemOut, unknown>[] {
  return [
    {
      accessorKey: 'key',
      header: t('workItems:columns.key'),
      cell: ({ row }) => <span className="font-mono text-xs text-text-secondary">{row.original.key}</span>,
    },
    {
      accessorKey: 'type',
      header: t('workItems:columns.type'),
      cell: ({ row }) => <Badge variant="outline">{t(`workItems:type.${row.original.type}`)}</Badge>,
    },
    {
      accessorKey: 'title',
      header: t('workItems:columns.title'),
      cell: ({ row }) => <span className="font-medium text-text-primary">{row.original.title}</span>,
    },
    {
      accessorKey: 'status',
      header: t('workItems:columns.status'),
      cell: ({ row }) => (
        <Badge variant={statusVariant[row.original.status]}>{t(`workItems:status.${row.original.status}`)}</Badge>
      ),
    },
    {
      accessorKey: 'priority',
      header: t('workItems:columns.priority'),
      cell: ({ row }) => (
        <Badge variant={priorityVariant[row.original.priority]}>
          {t(`workItems:priority.${row.original.priority}`)}
        </Badge>
      ),
    },
    {
      accessorKey: 'assignee',
      header: t('workItems:columns.assignee'),
      cell: ({ row }) => row.original.assignee?.displayName ?? t('workItems:noAssignee'),
    },
    {
      accessorKey: 'createdAt',
      header: t('workItems:columns.createdAt'),
      cell: ({ row }) => formatDateTime(row.original.createdAt),
    },
  ]
}
