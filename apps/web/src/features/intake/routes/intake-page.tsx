import type { IntakeSource, IntakeStatus } from '@worknexus/contracts'
import { Plus } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router'

import { DataTable } from '@/components/patterns/data-table'
import { EmptyState } from '@/components/patterns/empty-state'
import { ErrorState } from '@/components/patterns/error-state'
import { PageSkeleton } from '@/components/patterns/page-skeleton'
import { Button } from '@/components/ui/button'
import { INTAKE_SOURCES, INTAKE_STATUSES } from '@/features/intake/api/schemas'
import { useIntakeListQuery } from '@/features/intake/api/use-intake-list-query'
import { intakeColumns } from '@/features/intake/components/intake-columns'
import { IntakeDetailSheet } from '@/features/intake/components/intake-detail-sheet'
import { IntakeFormDialog } from '@/features/intake/components/intake-form-dialog'
import { PermissionGate } from '@/lib/auth/permission-gate'
import { paths } from '@/lib/paths'

const PAGE_SIZE = 20

const filterClassName =
  'h-9 rounded-md border border-border-default bg-surface-primary px-3 text-sm text-text-primary focus-visible:border-border-strong focus-visible:outline-none'

export function IntakePage() {
  const { t } = useTranslation(['common', 'intake'])
  const { projectId = '' } = useParams()
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<IntakeStatus | ''>('')
  const [source, setSource] = useState<IntakeSource | ''>('')
  const [createOpen, setCreateOpen] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const query = useIntakeListQuery(projectId, {
    page,
    page_size: PAGE_SIZE,
    status: status || undefined,
    source: source || undefined,
  })

  return (
    <div className="space-y-6">
      <Link to={paths.projectDetail(projectId)} className="text-sm text-text-muted hover:underline">
        ← {t('intake:backToProject')}
      </Link>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">{t('intake:title')}</h1>
          <p className="text-sm text-text-muted">{t('intake:description')}</p>
        </div>
        <PermissionGate permission="intake.create" projectId={projectId}>
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="size-4" />
            {t('intake:newButton')}
          </Button>
        </PermissionGate>
      </div>

      <div className="flex flex-wrap gap-2">
        <select
          className={filterClassName}
          value={status}
          onChange={(event) => {
            setStatus(event.target.value as IntakeStatus | '')
            setPage(1)
          }}
        >
          <option value="">{t('intake:filter.allStatus')}</option>
          {INTAKE_STATUSES.map((value) => (
            <option key={value} value={value}>
              {t(`intake:status.${value}`)}
            </option>
          ))}
        </select>
        <select
          className={filterClassName}
          value={source}
          onChange={(event) => {
            setSource(event.target.value as IntakeSource | '')
            setPage(1)
          }}
        >
          <option value="">{t('intake:filter.allSource')}</option>
          {INTAKE_SOURCES.map((value) => (
            <option key={value} value={value}>
              {t(`intake:source.${value}`)}
            </option>
          ))}
        </select>
      </div>

      {query.isPending ? (
        <PageSkeleton />
      ) : query.isError ? (
        <ErrorState onRetry={() => void query.refetch()} />
      ) : (
        <>
          <DataTable
            columns={intakeColumns(t, setSelectedId)}
            data={query.data.items}
            emptyState={<EmptyState description={t('intake:empty')} />}
          />
          {(() => {
            const totalPages = Math.max(1, Math.ceil(query.data.total / query.data.pageSize))
            return totalPages > 1 ? (
              <div className="flex items-center justify-end gap-2">
                <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                  {t('pagination.previous')}
                </Button>
                <span className="text-sm text-text-muted">{t('pagination.pageOf', { page, total: totalPages })}</span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  {t('pagination.next')}
                </Button>
              </div>
            ) : null
          })()}
        </>
      )}

      <IntakeFormDialog open={createOpen} onOpenChange={setCreateOpen} projectId={projectId} />
      <IntakeDetailSheet projectId={projectId} intakeId={selectedId} onClose={() => setSelectedId(null)} />
    </div>
  )
}
