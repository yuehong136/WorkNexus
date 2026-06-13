import { zodResolver } from '@hookform/resolvers/zod'
import { useMemo } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { memberAddSchema, type MemberAddValues } from '@/features/projects/api/schemas'
import { useAddMemberMutation } from '@/features/projects/api/use-add-member-mutation'
import { useTenantUsersQuery } from '@/features/projects/api/use-tenant-users-query'
import { cn } from '@/lib/utils'

const selectClassName =
  'flex h-9 w-full rounded-md border border-border-default bg-surface-primary px-3 py-1 text-sm text-text-primary focus-visible:border-border-strong focus-visible:outline-none'

const ROLES = ['member', 'viewer', 'project_admin'] as const

interface AddMemberDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  projectId: string
  excludedUserIds: string[]
}

export function AddMemberDialog({ open, onOpenChange, projectId, excludedUserIds }: AddMemberDialogProps) {
  const { t } = useTranslation(['common', 'projects'])
  const usersQuery = useTenantUsersQuery({ enabled: open })
  const mutation = useAddMemberMutation()

  const excluded = useMemo(() => new Set(excludedUserIds), [excludedUserIds])
  const eligible = (usersQuery.data?.items ?? []).filter((user) => !excluded.has(user.id))

  const form = useForm<MemberAddValues>({
    resolver: zodResolver(memberAddSchema(t)),
    defaultValues: { userId: '', role: 'member' },
  })

  const close = (next: boolean) => {
    if (!next) {
      form.reset()
      mutation.reset()
    }
    onOpenChange(next)
  }

  const onSubmit = form.handleSubmit((values) => {
    mutation.mutate(
      { projectId, body: { userId: values.userId, role: values.role } },
      {
        onSuccess: () => {
          toast.success(t('projects:members.added'))
          close(false)
        },
      },
    )
  })

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('projects:members.addTitle')}</DialogTitle>
          <DialogDescription>{t('projects:members.addDescription')}</DialogDescription>
        </DialogHeader>
        {eligible.length === 0 ? (
          <div className="space-y-4">
            <p className="text-sm text-text-muted">{t('projects:members.noEligibleUsers')}</p>
            <DialogFooter>
              <Button onClick={() => close(false)}>{t('actions.close')}</Button>
            </DialogFooter>
          </div>
        ) : (
          <Form {...form}>
            <form onSubmit={(event) => void onSubmit(event)} className="space-y-4" noValidate>
              <FormField
                control={form.control}
                name="userId"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('projects:members.user')}</FormLabel>
                    <FormControl>
                      <select className={cn(selectClassName)} {...field}>
                        <option value="" disabled>
                          {t('projects:members.userPlaceholder')}
                        </option>
                        {eligible.map((user) => (
                          <option key={user.id} value={user.id}>
                            {user.displayName} ({user.email})
                          </option>
                        ))}
                      </select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="role"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('projects:members.role')}</FormLabel>
                    <FormControl>
                      <select className={cn(selectClassName)} {...field}>
                        {ROLES.map((role) => (
                          <option key={role} value={role}>
                            {t(`projects:roles.${role}`)}
                          </option>
                        ))}
                      </select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => close(false)}>
                  {t('actions.cancel')}
                </Button>
                <Button type="submit" disabled={mutation.isPending}>
                  {t('projects:members.submit')}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        )}
      </DialogContent>
    </Dialog>
  )
}
