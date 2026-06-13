import type { WorkItemOut, WorkItemStatus } from '@worknexus/contracts'
import { Pencil, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/patterns/confirm-dialog'
import { ErrorState } from '@/components/patterns/error-state'
import { PageSkeleton } from '@/components/patterns/page-skeleton'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { ALLOWED_TRANSITIONS, CUSTOM_FIELDS_BY_TYPE } from '@/features/work-items/api/schemas'
import { useDeleteWorkItemMutation } from '@/features/work-items/api/use-delete-work-item-mutation'
import { useProjectMembersQuery } from '@/features/work-items/api/use-project-members-query'
import { useTransitionWorkItemMutation } from '@/features/work-items/api/use-transition-work-item-mutation'
import { useWorkItemQuery } from '@/features/work-items/api/use-work-item-query'
import { PriorityBadge, SourceBadge, StatusBadge, TypeBadge } from '@/features/work-items/components/work-item-badges'
import { WorkItemActivity } from '@/features/work-items/components/work-item-activity'
import { WorkItemComments } from '@/features/work-items/components/work-item-comments'
import { WorkItemEditForm } from '@/features/work-items/components/work-item-edit-form'
import { WorkItemRelations } from '@/features/work-items/components/work-item-relations'
import { useHasPermission } from '@/lib/auth/use-has-permission'
import { formatDateTime } from '@/lib/datetime'
import { Markdown } from '@/lib/markdown'
import { cn } from '@/lib/utils'

const selectClassName =
  'h-9 rounded-md border border-border-default bg-surface-primary px-3 text-sm text-text-primary focus-visible:border-border-strong focus-visible:outline-none'

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <dt className="text-xs text-text-muted">{label}</dt>
      <dd className="text-sm text-text-primary">{children}</dd>
    </div>
  )
}

function TransitionControl({ projectId, item }: { projectId: string; item: WorkItemOut }) {
  const { t } = useTranslation('workItems')
  const mutation = useTransitionWorkItemMutation(projectId, item.id)
  const allowed = ALLOWED_TRANSITIONS[item.status]
  if (allowed.length === 0) return <StatusBadge status={item.status} />
  return (
    <select
      className={cn(selectClassName)}
      value={item.status}
      disabled={mutation.isPending}
      onChange={(event) => {
        const next = event.target.value as WorkItemStatus
        if (next === item.status) return
        mutation.mutate({ status: next }, { onSuccess: () => toast.success(t('transition.success')) })
      }}
    >
      <option value={item.status}>{t(`status.${item.status}`)}</option>
      {allowed.map((status) => (
        <option key={status} value={status}>
          {t(`status.${status}`)}
        </option>
      ))}
    </select>
  )
}

function DrawerBody({
  projectId,
  workItemId,
  onClose,
}: {
  projectId: string
  workItemId: string
  onClose: () => void
}) {
  const { t } = useTranslation(['common', 'workItems'])
  const query = useWorkItemQuery(workItemId)
  const membersQuery = useProjectMembersQuery(projectId)
  const deleteMutation = useDeleteWorkItemMutation(projectId)
  const [editing, setEditing] = useState(false)
  const [removing, setRemoving] = useState(false)

  const canUpdate = useHasPermission('work_item.update', projectId)
  const canTransition = useHasPermission('work_item.transition', projectId)
  const canComment = useHasPermission('work_item.comment', projectId)
  const canDelete = useHasPermission('work_item.delete', projectId)

  if (query.isPending) {
    return (
      <>
        <SheetTitle className="sr-only">{t('workItems:title')}</SheetTitle>
        <PageSkeleton />
      </>
    )
  }
  if (query.isError) {
    return (
      <>
        <SheetTitle className="sr-only">{t('workItems:title')}</SheetTitle>
        <ErrorState onRetry={() => void query.refetch()} />
      </>
    )
  }

  const item = query.data
  const customKeys = CUSTOM_FIELDS_BY_TYPE[item.type].filter((key) => {
    const value = (item.customFields ?? {})[key]
    return value !== undefined && value !== null && value !== ''
  })

  return (
    <>
      <SheetHeader>
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs text-text-secondary">{item.key}</span>
          <TypeBadge type={item.type} />
          <SourceBadge source={item.source} />
        </div>
        <SheetTitle>{item.title}</SheetTitle>
      </SheetHeader>

      <div className="flex flex-wrap items-center gap-2">
        {canTransition ? <TransitionControl projectId={projectId} item={item} /> : <StatusBadge status={item.status} />}
        <PriorityBadge priority={item.priority} />
        {canUpdate && !editing ? (
          <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
            <Pencil className="size-4" />
            {t('workItems:detail.edit')}
          </Button>
        ) : null}
        {canDelete && !editing ? (
          <Button variant="outline" size="sm" onClick={() => setRemoving(true)}>
            <Trash2 className="size-4" />
            {t('workItems:detail.delete')}
          </Button>
        ) : null}
      </div>

      {editing ? (
        <WorkItemEditForm
          projectId={projectId}
          item={item}
          members={membersQuery.data ?? []}
          onDone={() => setEditing(false)}
        />
      ) : (
        <div className="space-y-5">
          <dl className="grid grid-cols-2 gap-4">
            <Field label={t('workItems:columns.assignee')}>
              {item.assignee?.displayName ?? t('workItems:noAssignee')}
            </Field>
            <Field label={t('workItems:detail.source')}>{t(`workItems:source.${item.source}`)}</Field>
            <Field label={t('workItems:detail.dueAt')}>
              {item.dueAt ? formatDateTime(item.dueAt) : t('workItems:detail.noDueAt')}
            </Field>
            <Field label={t('workItems:columns.createdAt')}>{formatDateTime(item.createdAt)}</Field>
          </dl>

          <div className="space-y-1">
            <p className="text-xs text-text-muted">{t('workItems:detail.descriptionLabel')}</p>
            {item.description ? (
              <Markdown content={item.description} />
            ) : (
              <p className="text-sm text-text-muted">{t('workItems:detail.noDescription')}</p>
            )}
          </div>

          {item.acceptanceCriteria ? (
            <div className="space-y-1">
              <p className="text-xs text-text-muted">{t('workItems:detail.acceptanceCriteria')}</p>
              <Markdown content={item.acceptanceCriteria} />
            </div>
          ) : null}

          {item.aiSummary ? (
            <div className="space-y-1 rounded-md border border-border-default bg-surface-secondary p-3">
              <p className="text-xs text-text-muted">{t('workItems:detail.aiSummary')}</p>
              <Markdown content={item.aiSummary} />
            </div>
          ) : null}

          {customKeys.length > 0 ? (
            <div className="space-y-2">
              <p className="text-xs text-text-muted">{t('workItems:detail.customFieldsSection')}</p>
              <dl className="grid grid-cols-2 gap-3">
                {customKeys.map((key) => {
                  const value = (item.customFields ?? {})[key]
                  return (
                    <Field key={key} label={t(`workItems:customFields.${key}`)}>
                      {Array.isArray(value) ? value.join(', ') : String(value)}
                    </Field>
                  )
                })}
              </dl>
            </div>
          ) : null}
        </div>
      )}

      <hr className="border-border-default" />
      <WorkItemRelations projectId={projectId} workItemId={item.id} canEdit={canUpdate} />
      <hr className="border-border-default" />
      <WorkItemComments workItemId={item.id} canComment={canComment} />
      <hr className="border-border-default" />
      <WorkItemActivity workItemId={item.id} />

      <ConfirmDialog
        open={removing}
        onOpenChange={setRemoving}
        title={t('workItems:remove.title')}
        description={t('workItems:remove.description', { title: item.title })}
        destructive
        loading={deleteMutation.isPending}
        onConfirm={() =>
          deleteMutation.mutate(item.id, {
            onSuccess: () => {
              toast.success(t('workItems:remove.success'))
              setRemoving(false)
              onClose()
            },
          })
        }
      />
    </>
  )
}

export function WorkItemDrawer({
  projectId,
  workItemId,
  onClose,
}: {
  projectId: string
  workItemId: string | null
  onClose: () => void
}) {
  return (
    <Sheet
      open={workItemId !== null}
      onOpenChange={(open) => {
        if (!open) onClose()
      }}
    >
      <SheetContent aria-describedby={undefined}>
        {workItemId !== null ? <DrawerBody projectId={projectId} workItemId={workItemId} onClose={onClose} /> : null}
      </SheetContent>
    </Sheet>
  )
}
