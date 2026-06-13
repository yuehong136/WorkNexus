import type { WorkItemPriority, WorkItemStatus, WorkItemType } from '@worknexus/contracts'
import { Columns3, Plus } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router'

import { DataTable } from '@/components/patterns/data-table'
import { EmptyState } from '@/components/patterns/empty-state'
import { ErrorState } from '@/components/patterns/error-state'
import { PageSkeleton } from '@/components/patterns/page-skeleton'
import { Button } from '@/components/ui/button'
import {
  WORK_ITEM_PRIORITIES,
  WORK_ITEM_STATUSES,
  WORK_ITEM_TYPES,
} from '@/features/work-items/api/schemas'
import { useProjectMembersQuery } from '@/features/work-items/api/use-project-members-query'
import { useWorkItemsQuery } from '@/features/work-items/api/use-work-items-query'
import { WorkItemDrawer } from '@/features/work-items/components/work-item-drawer'
import { workItemColumns } from '@/features/work-items/components/work-items-columns'
import { WorkItemFormDialog } from '@/features/work-items/components/work-item-form-dialog'
import { PermissionGate } from '@/lib/auth/permission-gate'
import { paths } from '@/lib/paths'

const PAGE_SIZE = 20

const filterClassName =
  'h-9 rounded-md border border-border-default bg-surface-primary px-3 text-sm text-text-primary focus-visible:border-border-strong focus-visible:outline-none'

export function WorkItemsPage() {
  const { t } = useTranslation(['common', 'workItems'])
  const { projectId = '' } = useParams()
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<WorkItemStatus | ''>('')
  const [type, setType] = useState<WorkItemType | ''>('')
  const [priority, setPriority] = useState<WorkItemPriority | ''>('')
  const [assigneeId, setAssigneeId] = useState('')
  const [createOpen, setCreateOpen] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const membersQuery = useProjectMembersQuery(projectId)
  const query = useWorkItemsQuery(projectId, {
    page,
    page_size: PAGE_SIZE,
    status: status || undefined,
    type: type || undefined,
    priority: priority || undefined,
    assignee_id: assigneeId || undefined,
  })

  return (
    <div className="space-y-6">
      <Link to={paths.projectDetail(projectId)} className="text-sm text-text-muted hover:underline">
        ← {t('workItems:backToProject')}
      </Link>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">{t('workItems:title')}</h1>
          <p className="text-sm text-text-muted">{t('workItems:description')}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => void navigate(paths.board(projectId))}>
            <Columns3 className="size-4" />
            {t('workItems:board.boardView')}
          </Button>
          <PermissionGate permission="work_item.create" projectId={projectId}>
            <Button onClick={() => setCreateOpen(true)}>
              <Plus className="size-4" />
              {t('workItems:newButton')}
            </Button>
          </PermissionGate>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <select
          className={filterClassName}
          value={type}
          onChange={(event) => {
            setType(event.target.value as WorkItemType | '')
            setPage(1)
          }}
        >
          <option value="">{t('workItems:filter.allType')}</option>
          {WORK_ITEM_TYPES.map((value) => (
            <option key={value} value={value}>
              {t(`workItems:type.${value}`)}
            </option>
          ))}
        </select>
        <select
          className={filterClassName}
          value={status}
          onChange={(event) => {
            setStatus(event.target.value as WorkItemStatus | '')
            setPage(1)
          }}
        >
          <option value="">{t('workItems:filter.allStatus')}</option>
          {WORK_ITEM_STATUSES.map((value) => (
            <option key={value} value={value}>
              {t(`workItems:status.${value}`)}
            </option>
          ))}
        </select>
        <select
          className={filterClassName}
          value={priority}
          onChange={(event) => {
            setPriority(event.target.value as WorkItemPriority | '')
            setPage(1)
          }}
        >
          <option value="">{t('workItems:filter.allPriority')}</option>
          {WORK_ITEM_PRIORITIES.map((value) => (
            <option key={value} value={value}>
              {t(`workItems:priority.${value}`)}
            </option>
          ))}
        </select>
        <select
          className={filterClassName}
          value={assigneeId}
          onChange={(event) => {
            setAssigneeId(event.target.value)
            setPage(1)
          }}
        >
          <option value="">{t('workItems:filter.allAssignee')}</option>
          {(membersQuery.data ?? []).map((member) => (
            <option key={member.userId} value={member.userId}>
              {member.displayName}
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
            columns={workItemColumns(t, setSelectedId)}
            data={query.data.items}
            emptyState={<EmptyState description={t('workItems:empty')} />}
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

      <WorkItemFormDialog open={createOpen} onOpenChange={setCreateOpen} projectId={projectId} />
      <WorkItemDrawer projectId={projectId} workItemId={selectedId} onClose={() => setSelectedId(null)} />
    </div>
  )
}
