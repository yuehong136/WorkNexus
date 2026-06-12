import type { InviteOut } from '@worknexus/contracts'
import { UserPlus } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/patterns/confirm-dialog'
import { DataTable } from '@/components/patterns/data-table'
import { EmptyState } from '@/components/patterns/empty-state'
import { ErrorState } from '@/components/patterns/error-state'
import { PageSkeleton } from '@/components/patterns/page-skeleton'
import { Button } from '@/components/ui/button'
import { inviteColumns, userColumns } from '@/features/settings/components/members-columns'
import { InviteDialog } from '@/features/settings/components/invite-dialog'
import { useInvitesQuery } from '@/features/settings/api/use-invites-query'
import { useRevokeInviteMutation } from '@/features/settings/api/use-revoke-invite-mutation'
import { useUsersQuery } from '@/features/settings/api/use-users-query'
import { PermissionGate } from '@/lib/auth/permission-gate'
import { useHasPermission } from '@/lib/auth/use-has-permission'

const PAGE_SIZE = 20

export function MembersPage() {
  const { t } = useTranslation(['common', 'auth', 'settings'])
  const [page, setPage] = useState(1)
  const [inviteOpen, setInviteOpen] = useState(false)
  const [revokeTarget, setRevokeTarget] = useState<InviteOut | null>(null)

  const canInvite = useHasPermission('user.invite')
  const usersQuery = useUsersQuery({ page, pageSize: PAGE_SIZE })
  const invitesQuery = useInvitesQuery({ page: 1, pageSize: 50 }, { enabled: canInvite })
  const revokeMutation = useRevokeInviteMutation()

  if (usersQuery.isPending) return <PageSkeleton />
  if (usersQuery.isError) return <ErrorState onRetry={() => void usersQuery.refetch()} />

  const users = usersQuery.data
  const totalPages = Math.max(1, Math.ceil(users.total / users.pageSize))

  const confirmRevoke = () => {
    if (!revokeTarget) return
    revokeMutation.mutate(revokeTarget.id, {
      onSuccess: () => {
        toast.success(t('settings:invite.revoked'))
        setRevokeTarget(null)
      },
    })
  }

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">{t('settings:members.title')}</h1>
          <p className="text-sm text-text-muted">{t('settings:members.description')}</p>
        </div>
        <PermissionGate permission="user.invite">
          <Button onClick={() => setInviteOpen(true)}>
            <UserPlus className="size-4" />
            {t('settings:invite.button')}
          </Button>
        </PermissionGate>
      </div>

      <DataTable columns={userColumns(t)} data={users.items} />
      {totalPages > 1 ? (
        <div className="flex items-center justify-end gap-2">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            {t('pagination.previous')}
          </Button>
          <span className="text-sm text-text-muted">
            {t('pagination.pageOf', { page, total: totalPages })}
          </span>
          <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
            {t('pagination.next')}
          </Button>
        </div>
      ) : null}

      <PermissionGate permission="user.invite">
        <section className="space-y-3">
          <h2 className="text-base font-semibold text-text-primary">{t('settings:members.invitesSection')}</h2>
          {invitesQuery.isError ? (
            <ErrorState onRetry={() => void invitesQuery.refetch()} />
          ) : (
            <DataTable
              columns={inviteColumns(t, (invite) =>
                invite.status === 'pending' ? (
                  <Button variant="ghost" size="sm" onClick={() => setRevokeTarget(invite)}>
                    {t('settings:invite.revoke')}
                  </Button>
                ) : null,
              )}
              data={invitesQuery.data?.items ?? []}
              emptyState={<EmptyState description={t('settings:invite.empty')} />}
            />
          )}
        </section>
      </PermissionGate>

      <InviteDialog open={inviteOpen} onOpenChange={setInviteOpen} />
      <ConfirmDialog
        open={revokeTarget !== null}
        onOpenChange={(open) => {
          if (!open) setRevokeTarget(null)
        }}
        title={t('settings:invite.revokeTitle')}
        description={t('settings:invite.revokeDescription', { email: revokeTarget?.email ?? '' })}
        destructive
        loading={revokeMutation.isPending}
        onConfirm={confirmRevoke}
      />
    </div>
  )
}
