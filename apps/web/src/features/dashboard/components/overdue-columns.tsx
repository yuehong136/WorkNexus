import type { ColumnDef } from '@tanstack/react-table'
import type { DashboardOverdueItemOut } from '@worknexus/contracts'

import { formatDate } from '@/lib/datetime'
import type { AppTFunction } from '@/locales/i18n'

export function overdueColumns(t: AppTFunction): ColumnDef<DashboardOverdueItemOut, unknown>[] {
  return [
    {
      accessorKey: 'key',
      header: t('dashboard:overdue.columns.key'),
      cell: ({ row }) => <span className="font-mono text-xs text-text-secondary">{row.original.key}</span>,
    },
    {
      accessorKey: 'title',
      header: t('dashboard:overdue.columns.title'),
      cell: ({ row }) => <span className="font-medium text-text-primary">{row.original.title}</span>,
    },
    {
      accessorKey: 'priority',
      header: t('dashboard:overdue.columns.priority'),
      cell: ({ row }) => t(`workItems:priority.${row.original.priority}`),
    },
    {
      accessorKey: 'assignee',
      header: t('dashboard:overdue.columns.assignee'),
      cell: ({ row }) => row.original.assignee?.displayName ?? t('dashboard:overdue.unassigned'),
    },
    {
      accessorKey: 'dueAt',
      header: t('dashboard:overdue.columns.dueAt'),
      cell: ({ row }) => formatDate(row.original.dueAt),
    },
    {
      accessorKey: 'daysOverdue',
      header: t('dashboard:overdue.columns.daysOverdue'),
      cell: ({ row }) => (
        <span className="text-status-error">{t('dashboard:overdue.daysValue', { count: row.original.daysOverdue })}</span>
      ),
    },
  ]
}
