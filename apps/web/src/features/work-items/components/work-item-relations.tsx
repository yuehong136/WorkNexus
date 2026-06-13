import type { RelationOut, RelationType } from '@worknexus/contracts'
import { Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/patterns/confirm-dialog'
import { Button } from '@/components/ui/button'
import { workItemErrorMessage } from '@/features/work-items/api/error-messages'
import { MANUAL_RELATION_TYPES } from '@/features/work-items/api/schemas'
import { useCreateRelationMutation } from '@/features/work-items/api/use-create-relation-mutation'
import { useDeleteRelationMutation } from '@/features/work-items/api/use-delete-relation-mutation'
import { useWorkItemRelationsQuery } from '@/features/work-items/api/use-work-item-relations-query'
import { useWorkItemsQuery } from '@/features/work-items/api/use-work-items-query'
import type { AppTFunction } from '@/locales/i18n'
import { cn } from '@/lib/utils'

const selectClassName =
  'h-9 rounded-md border border-border-default bg-surface-primary px-3 text-sm text-text-primary focus-visible:border-border-strong focus-visible:outline-none'

function relationLabel(relation: RelationOut, t: AppTFunction): string {
  if (relation.type === 'blocks') {
    return t(
      relation.direction === 'incoming' ? 'workItems:relationType.blocked_by' : 'workItems:relationType.blocks',
    )
  }
  const base = t(`workItems:relationType.${relation.type}`)
  return relation.direction === 'incoming' ? `${base} (${t('workItems:relationDirection.incoming')})` : base
}

export function WorkItemRelations({
  projectId,
  workItemId,
  canEdit,
}: {
  projectId: string
  workItemId: string
  canEdit: boolean
}) {
  const { t } = useTranslation(['common', 'workItems'])
  const relationsQuery = useWorkItemRelationsQuery(workItemId)
  const candidatesQuery = useWorkItemsQuery(projectId, { page: 1, page_size: 100 })
  const createMutation = useCreateRelationMutation(workItemId)
  const deleteMutation = useDeleteRelationMutation(workItemId)
  const [type, setType] = useState<RelationType>('relates_to')
  const [target, setTarget] = useState('')
  const [removing, setRemoving] = useState<string | null>(null)

  const relations = relationsQuery.data ?? []
  const candidates = (candidatesQuery.data?.items ?? []).filter((item) => item.id !== workItemId)
  const errorMessage = workItemErrorMessage(createMutation.error, t)

  const add = () => {
    if (!target) return
    createMutation.mutate(
      { type, targetWorkItemId: target },
      {
        onSuccess: () => {
          setTarget('')
          toast.success(t('workItems:relations.added'))
        },
      },
    )
  }

  return (
    <section className="space-y-3">
      <h3 className="text-sm font-medium text-text-secondary">{t('workItems:relations.title')}</h3>
      {relations.length > 0 ? (
        <ul className="space-y-2">
          {relations.map((relation) => (
            <li
              key={relation.id}
              className="flex items-center justify-between gap-2 rounded-md border border-border-default bg-surface-primary p-2 text-sm"
            >
              <span className="flex min-w-0 items-center gap-2">
                <span className="shrink-0 text-text-muted">{relationLabel(relation, t)}</span>
                <span className="shrink-0 font-mono text-xs text-text-secondary">{relation.related.key}</span>
                <span className="truncate text-text-primary">{relation.related.title}</span>
              </span>
              {canEdit ? (
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={t('workItems:relations.removeTitle')}
                  onClick={() => setRemoving(relation.id)}
                >
                  <Trash2 className="size-4" />
                </Button>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-text-muted">{t('workItems:relations.empty')}</p>
      )}

      {canEdit ? (
        candidates.length === 0 ? (
          <p className="text-sm text-text-muted">{t('workItems:relations.noOther')}</p>
        ) : (
          <div className="space-y-2">
            <div className="flex flex-wrap gap-2">
              <select
                className={cn(selectClassName)}
                value={type}
                onChange={(event) => setType(event.target.value as RelationType)}
              >
                {MANUAL_RELATION_TYPES.map((value) => (
                  <option key={value} value={value}>
                    {t(`workItems:relationType.${value}`)}
                  </option>
                ))}
              </select>
              <select
                className={cn(selectClassName, 'min-w-48 flex-1')}
                value={target}
                onChange={(event) => setTarget(event.target.value)}
              >
                <option value="">{t('workItems:relations.targetPlaceholder')}</option>
                {candidates.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.key} · {item.title}
                  </option>
                ))}
              </select>
              <Button size="sm" disabled={createMutation.isPending || !target} onClick={add}>
                {t('workItems:relations.submit')}
              </Button>
            </div>
            {errorMessage ? <p className="text-sm text-status-error">{errorMessage}</p> : null}
          </div>
        )
      ) : null}

      <ConfirmDialog
        open={removing !== null}
        onOpenChange={(open) => {
          if (!open) setRemoving(null)
        }}
        title={t('workItems:relations.removeTitle')}
        description={t('workItems:relations.removeDescription')}
        destructive
        loading={deleteMutation.isPending}
        onConfirm={() => {
          if (!removing) return
          deleteMutation.mutate(removing, {
            onSuccess: () => {
              toast.success(t('workItems:relations.removed'))
              setRemoving(null)
            },
          })
        }}
      />
    </section>
  )
}
