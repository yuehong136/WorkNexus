import type { ColumnDef } from '@tanstack/react-table'
import type { IntakeOut } from '@worknexus/contracts'

import { IntakeSourceBadge, IntakeStatusBadge } from '@/features/intake/components/intake-badges'
import { formatDateTime } from '@/lib/datetime'
import type { AppTFunction } from '@/locales/i18n'

export function intakeColumns(t: AppTFunction, onSelect: (id: string) => void): ColumnDef<IntakeOut, unknown>[] {
  return [
    {
      accessorKey: 'title',
      header: t('intake:columns.title'),
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
      header: t('intake:columns.status'),
      cell: ({ row }) => <IntakeStatusBadge status={row.original.status} />,
    },
    {
      accessorKey: 'source',
      header: t('intake:columns.source'),
      cell: ({ row }) => <IntakeSourceBadge source={row.original.source} />,
    },
    {
      accessorKey: 'suggestedType',
      header: t('intake:columns.suggestedType'),
      cell: ({ row }) =>
        row.original.suggestedType ? t(`workItems:type.${row.original.suggestedType}`) : '-',
    },
    {
      accessorKey: 'createdAt',
      header: t('intake:columns.createdAt'),
      cell: ({ row }) => formatDateTime(row.original.createdAt),
    },
  ]
}
