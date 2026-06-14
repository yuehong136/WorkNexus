import type { ColumnDef } from '@tanstack/react-table'
import type { SkillInvocationOut } from '@worknexus/contracts'

import { formatDateTime } from '@/lib/datetime'
import type { AppTFunction } from '@/locales/i18n'

import { InvocationStatusBadge, RiskBadge } from './skill-badges'

export function skillInvocationColumns(
  t: AppTFunction,
  onSelect: (id: string) => void,
): ColumnDef<SkillInvocationOut, unknown>[] {
  return [
    {
      accessorKey: 'toolName',
      header: t('skills:columns.tool'),
      cell: ({ row }) => (
        <button
          type="button"
          onClick={() => onSelect(row.original.id)}
          className="text-left font-mono text-xs text-text-primary hover:underline"
        >
          {row.original.toolName}
        </button>
      ),
    },
    {
      accessorKey: 'skillCode',
      header: t('skills:columns.skill'),
      cell: ({ row }) => <span className="text-xs text-text-secondary">{row.original.skillCode}</span>,
    },
    {
      accessorKey: 'riskLevel',
      header: t('skills:columns.risk'),
      cell: ({ row }) => <RiskBadge risk={row.original.riskLevel} />,
    },
    {
      accessorKey: 'status',
      header: t('skills:columns.status'),
      cell: ({ row }) => <InvocationStatusBadge status={row.original.status} />,
    },
    {
      id: 'user',
      header: t('skills:columns.user'),
      cell: ({ row }) => row.original.representedUser?.displayName ?? t('skills:common.none'),
    },
    {
      accessorKey: 'requiresConfirmation',
      header: t('skills:columns.requiresConfirmation'),
      cell: ({ row }) => (row.original.requiresConfirmation ? t('skills:common.yes') : t('skills:common.no')),
    },
    {
      id: 'agentAction',
      header: t('skills:columns.agentAction'),
      cell: ({ row }) => row.original.agentActionId ?? t('skills:common.none'),
    },
    {
      accessorKey: 'createdAt',
      header: t('skills:columns.time'),
      cell: ({ row }) => formatDateTime(row.original.createdAt),
    },
  ]
}
