import type { ColumnDef } from '@tanstack/react-table'
import type { WorkloadItemOut } from '@worknexus/contracts'

import type { AppTFunction } from '@/locales/i18n'

export function workloadColumns(t: AppTFunction): ColumnDef<WorkloadItemOut, unknown>[] {
  return [
    {
      accessorKey: 'assignee',
      header: t('dashboard:workload.assignee'),
      cell: ({ row }) => (
        <span className="text-text-primary">
          {row.original.assignee?.displayName ?? t('dashboard:workload.unassigned')}
        </span>
      ),
    },
    {
      accessorKey: 'totalCount',
      header: t('dashboard:workload.total'),
      cell: ({ row }) => row.original.totalCount,
    },
    {
      accessorKey: 'overdueCount',
      header: t('dashboard:workload.overdue'),
      cell: ({ row }) =>
        row.original.overdueCount > 0 ? (
          <span className="text-status-error">{row.original.overdueCount}</span>
        ) : (
          row.original.overdueCount
        ),
    },
    {
      accessorKey: 'highPriorityCount',
      header: t('dashboard:workload.highPriority'),
      cell: ({ row }) => row.original.highPriorityCount,
    },
  ]
}
