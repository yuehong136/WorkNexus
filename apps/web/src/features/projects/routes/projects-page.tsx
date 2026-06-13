import type { ProjectStatus } from '@worknexus/contracts'
import { FolderPlus } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { DataTable } from '@/components/patterns/data-table'
import { EmptyState } from '@/components/patterns/empty-state'
import { ErrorState } from '@/components/patterns/error-state'
import { PageSkeleton } from '@/components/patterns/page-skeleton'
import { Button } from '@/components/ui/button'
import { projectColumns } from '@/features/projects/components/projects-columns'
import { ProjectFormDialog } from '@/features/projects/components/project-form-dialog'
import { useProjectsListQuery } from '@/features/projects/api/use-projects-query'
import { PermissionGate } from '@/lib/auth/permission-gate'
import { cn } from '@/lib/utils'

const PAGE_SIZE = 20
const STATUSES: ProjectStatus[] = ['active', 'archived']

export function ProjectsPage() {
  const { t } = useTranslation(['common', 'projects'])
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<ProjectStatus>('active')
  const [createOpen, setCreateOpen] = useState(false)

  const projectsQuery = useProjectsListQuery({ page, pageSize: PAGE_SIZE, status })

  const changeStatus = (next: ProjectStatus) => {
    setStatus(next)
    setPage(1)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">{t('projects:title')}</h1>
          <p className="text-sm text-text-muted">{t('projects:description')}</p>
        </div>
        <PermissionGate permission="project.create">
          <Button onClick={() => setCreateOpen(true)}>
            <FolderPlus className="size-4" />
            {t('projects:create.button')}
          </Button>
        </PermissionGate>
      </div>

      <div className="flex gap-1">
        {STATUSES.map((value) => (
          <Button
            key={value}
            variant="ghost"
            size="sm"
            className={cn(status === value && 'bg-surface-secondary text-text-primary')}
            onClick={() => changeStatus(value)}
          >
            {t(`projects:filter.${value}`)}
          </Button>
        ))}
      </div>

      {projectsQuery.isPending ? (
        <PageSkeleton />
      ) : projectsQuery.isError ? (
        <ErrorState onRetry={() => void projectsQuery.refetch()} />
      ) : (
        <>
          <DataTable
            columns={projectColumns(t)}
            data={projectsQuery.data.items}
            emptyState={<EmptyState description={t('projects:empty')} />}
          />
          {(() => {
            const totalPages = Math.max(1, Math.ceil(projectsQuery.data.total / projectsQuery.data.pageSize))
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

      <ProjectFormDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  )
}
