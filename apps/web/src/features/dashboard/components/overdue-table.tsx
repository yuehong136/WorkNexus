import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { DataTable } from '@/components/patterns/data-table'
import { EmptyState } from '@/components/patterns/empty-state'
import { ErrorState } from '@/components/patterns/error-state'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useDashboardOverdueQuery } from '@/features/dashboard/api/use-dashboard-overdue-query'
import { overdueColumns } from '@/features/dashboard/components/overdue-columns'

const PAGE_SIZE = 10

export function OverdueTable({ projectId }: { projectId: string }) {
  const { t } = useTranslation(['common', 'dashboard', 'workItems'])
  const [page, setPage] = useState(1)
  const query = useDashboardOverdueQuery(projectId, { page, page_size: PAGE_SIZE })

  return (
    <section className="space-y-3">
      <h3 className="text-sm font-medium text-text-secondary">{t('dashboard:overdue.title')}</h3>
      {query.isPending ? (
        <Skeleton className="h-40 w-full" />
      ) : query.isError ? (
        <ErrorState onRetry={() => void query.refetch()} />
      ) : (
        <>
          <DataTable
            columns={overdueColumns(t)}
            data={query.data.items}
            emptyState={<EmptyState description={t('dashboard:overdue.empty')} />}
          />
          {(() => {
            const totalPages = Math.max(1, Math.ceil(query.data.total / query.data.pageSize))
            return totalPages > 1 ? (
              <div className="flex items-center justify-end gap-2">
                <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                  {t('common:pagination.previous')}
                </Button>
                <span className="text-sm text-text-muted">
                  {t('common:pagination.pageOf', { page, total: totalPages })}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  {t('common:pagination.next')}
                </Button>
              </div>
            ) : null
          })()}
        </>
      )}
    </section>
  )
}
