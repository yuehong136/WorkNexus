import type { ColumnDef } from '@tanstack/react-table'
import type { AuditLogOut } from '@worknexus/contracts'

import { formatDateTime } from '@/lib/datetime'
import type { AppTFunction } from '@/locales/i18n'

import { ActorBadge } from './audit-badges'

export function auditColumns(t: AppTFunction, onSelect: (log: AuditLogOut) => void): ColumnDef<AuditLogOut, unknown>[] {
  return [
    {
      accessorKey: 'createdAt',
      header: t('audit:columns.time'),
      cell: ({ row }) => (
        <span className="whitespace-nowrap text-xs text-text-secondary">{formatDateTime(row.original.createdAt)}</span>
      ),
    },
    {
      id: 'actor',
      header: t('audit:columns.actor'),
      cell: ({ row }) => <ActorBadge type={row.original.actor.type} name={row.original.actor.displayName} />,
    },
    {
      accessorKey: 'action',
      header: t('audit:columns.action'),
      cell: ({ row }) => (
        <button
          type="button"
          onClick={() => onSelect(row.original)}
          className="text-left font-mono text-xs text-text-primary hover:underline"
        >
          {row.original.action}
        </button>
      ),
    },
    {
      id: 'resource',
      header: t('audit:columns.resource'),
      cell: ({ row }) => (
        <span className="font-mono text-xs text-text-secondary">
          {row.original.resourceType}
          {row.original.resourceId ? `:${row.original.resourceId.slice(0, 8)}` : ''}
        </span>
      ),
    },
    {
      id: 'project',
      header: t('audit:columns.project'),
      cell: ({ row }) => <span className="text-xs text-text-secondary">{row.original.projectName ?? '—'}</span>,
    },
  ]
}
