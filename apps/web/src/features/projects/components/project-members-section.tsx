import type { ProjectMemberOut, ProjectMemberRole } from '@worknexus/contracts'
import { UserPlus } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/patterns/confirm-dialog'
import { DataTable } from '@/components/patterns/data-table'
import { EmptyState } from '@/components/patterns/empty-state'
import { ErrorState } from '@/components/patterns/error-state'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { AddMemberDialog } from '@/features/projects/components/add-member-dialog'
import { memberColumns } from '@/features/projects/components/member-columns'
import { useProjectMembersQuery } from '@/features/projects/api/use-project-members-query'
import { useRemoveMemberMutation } from '@/features/projects/api/use-remove-member-mutation'
import { useUpdateMemberRoleMutation } from '@/features/projects/api/use-update-member-role-mutation'

interface ProjectMembersSectionProps {
  projectId: string
  ownerId: string | null
  canManage: boolean
}

export function ProjectMembersSection({ projectId, ownerId, canManage }: ProjectMembersSectionProps) {
  const { t } = useTranslation(['common', 'projects'])
  const [addOpen, setAddOpen] = useState(false)
  const [removeTarget, setRemoveTarget] = useState<ProjectMemberOut | null>(null)

  const membersQuery = useProjectMembersQuery(projectId)
  const updateRoleMutation = useUpdateMemberRoleMutation()
  const removeMutation = useRemoveMemberMutation()

  const members = membersQuery.data ?? []
  const excludedUserIds = [...members.map((m) => m.userId), ...(ownerId ? [ownerId] : [])]

  const handleRoleChange = (member: ProjectMemberOut, role: ProjectMemberRole) => {
    if (member.role === role) return
    updateRoleMutation.mutate(
      { projectId, userId: member.userId, body: { role } },
      { onSuccess: () => toast.success(t('projects:members.roleUpdated')) },
    )
  }

  const confirmRemove = () => {
    if (!removeTarget) return
    removeMutation.mutate(
      { projectId, userId: removeTarget.userId },
      {
        onSuccess: () => {
          toast.success(t('projects:members.removed'))
          setRemoveTarget(null)
        },
      },
    )
  }

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-text-primary">{t('projects:members.title')}</h2>
        {canManage ? (
          <Button size="sm" onClick={() => setAddOpen(true)}>
            <UserPlus className="size-4" />
            {t('projects:members.add')}
          </Button>
        ) : null}
      </div>

      {membersQuery.isPending ? (
        <Skeleton className="h-32 w-full" />
      ) : membersQuery.isError ? (
        <ErrorState onRetry={() => void membersQuery.refetch()} />
      ) : (
        <DataTable
          columns={memberColumns(t, {
            canManage,
            pending: updateRoleMutation.isPending || removeMutation.isPending,
            onRoleChange: handleRoleChange,
            onRemove: setRemoveTarget,
          })}
          data={members}
          emptyState={<EmptyState description={t('projects:members.empty')} />}
        />
      )}

      {canManage ? (
        <AddMemberDialog
          open={addOpen}
          onOpenChange={setAddOpen}
          projectId={projectId}
          excludedUserIds={excludedUserIds}
        />
      ) : null}
      <ConfirmDialog
        open={removeTarget !== null}
        onOpenChange={(open) => {
          if (!open) setRemoveTarget(null)
        }}
        title={t('projects:members.removeTitle')}
        description={t('projects:members.removeDescription', { name: removeTarget?.displayName ?? '' })}
        destructive
        loading={removeMutation.isPending}
        onConfirm={confirmRemove}
      />
    </section>
  )
}
