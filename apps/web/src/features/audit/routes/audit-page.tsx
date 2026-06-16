import { type AuditAction, type AuditLogOut, type ListAuditLogsParams } from '@worknexus/contracts'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { DataTable } from '@/components/patterns/data-table'
import { EmptyState } from '@/components/patterns/empty-state'
import { ErrorState } from '@/components/patterns/error-state'
import { PageSkeleton } from '@/components/patterns/page-skeleton'
import { Button } from '@/components/ui/button'
import { useAuditLogsQuery } from '@/features/audit/api/use-audit-logs-query'
import { auditColumns } from '@/features/audit/components/audit-columns'
import { AuditDetailSheet } from '@/features/audit/components/audit-detail-sheet'
import { AuditFilterBar } from '@/features/audit/components/audit-filter-bar'
import { type AuditFilters, emptyAuditFilters } from '@/features/audit/components/audit-filters'

const PAGE_SIZE = 20

export function AuditPage() {
  const { t } = useTranslation(['common', 'audit'])
  const [filters, setFilters] = useState<AuditFilters>(emptyAuditFilters)
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<AuditLogOut | null>(null)

  const params: ListAuditLogsParams = {
    page,
    page_size: PAGE_SIZE,
    actor_type: filters.actorType || undefined,
    action: (filters.action || undefined) as AuditAction | undefined,
    resource_type: filters.resourceType || undefined,
    resource_id: filters.resourceId || undefined,
    project_id: filters.projectId || undefined,
    created_from: filters.fromDate ? `${filters.fromDate}T00:00:00` : undefined,
    created_to: filters.toDate ? `${filters.toDate}T23:59:59` : undefined,
  }

  const query = useAuditLogsQuery(params)
  const totalPages = query.data ? Math.max(1, Math.ceil(query.data.total / query.data.pageSize)) : 1

  const applyFilters = (next: AuditFilters) => {
    setFilters(next)
    setPage(1)
  }
  const viewChain = (resourceType: string, resourceId: string) => {
    setFilters({ ...emptyAuditFilters, resourceType, resourceId })
    setPage(1)
    setSelected(null)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t('audit:title')}</h1>
        <p className="text-sm text-text-muted">{t('audit:description')}</p>
      </div>

      <AuditFilterBar filters={filters} onChange={applyFilters} />

      {query.isPending ? (
        <PageSkeleton />
      ) : query.isError ? (
        <ErrorState onRetry={() => void query.refetch()} />
      ) : (
        <>
          <DataTable
            columns={auditColumns(t, setSelected)}
            data={query.data.items}
            emptyState={<EmptyState description={t('audit:empty')} />}
          />
          {totalPages > 1 ? (
            <div className="flex items-center justify-end gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                {t('pagination.previous')}
              </Button>
              <span className="text-sm text-text-muted">{t('pagination.pageOf', { page, total: totalPages })}</span>
              <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
                {t('pagination.next')}
              </Button>
            </div>
          ) : null}
        </>
      )}

      <AuditDetailSheet
        log={selected}
        open={selected !== null}
        onOpenChange={(open) => {
          if (!open) setSelected(null)
        }}
        onViewChain={viewChain}
      />
    </div>
  )
}
