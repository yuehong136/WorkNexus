import type { ColumnDef } from '@tanstack/react-table'
import type { WorkItemOut } from '@worknexus/contracts'

import { PriorityBadge, StatusBadge, TypeBadge } from '@/features/work-items/components/work-item-badges'
import { formatDateTime } from '@/lib/datetime'
import type { AppTFunction } from '@/locales/i18n'

export function workItemColumns(
  t: AppTFunction,
  onSelect: (id: string) => void,
): ColumnDef<WorkItemOut, unknown>[] {
  return [
    {
      accessorKey: 'key',
      header: t('workItems:columns.key'),
      cell: ({ row }) => <span className="font-mono text-xs text-text-secondary">{row.original.key}</span>,
    },
    {
      accessorKey: 'type',
      header: t('workItems:columns.type'),
      cell: ({ row }) => <TypeBadge type={row.original.type} />,
    },
    {
      accessorKey: 'title',
      header: t('workItems:columns.title'),
      cell: ({ row }) => (
        <button
          type="button"
          onClick={() => onSelect(row.original.id)}
          className="text-left font-medium text-text-primary hover:underline"
        >
          {row.original.title}
        </button>
      ),
    },
    {
      accessorKey: 'status',
      header: t('workItems:columns.status'),
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
    {
      accessorKey: 'priority',
      header: t('workItems:columns.priority'),
      cell: ({ row }) => <PriorityBadge priority={row.original.priority} />,
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
