import { zodResolver } from '@hookform/resolvers/zod'
import { Copy } from 'lucide-react'
import { useMemo, useState } from 'react'
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
import { Input } from '@/components/ui/input'
import { authErrorMessage } from '@/features/auth/api/error-messages'
import { inviteSchema, type InviteFormValues } from '@/features/settings/api/schemas'
import { useCreateInviteMutation } from '@/features/settings/api/use-create-invite-mutation'
import { useMeQuery } from '@/lib/auth/use-me-query'
import { paths } from '@/lib/paths'
import { cn } from '@/lib/utils'

const selectClassName =
  'flex h-9 w-full rounded-md border border-border-default bg-surface-primary px-3 py-1 text-sm text-text-primary focus-visible:border-border-strong focus-visible:outline-none'

interface InviteDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function InviteDialog({ open, onOpenChange }: InviteDialogProps) {
  const { t } = useTranslation(['common', 'auth', 'settings'])
  const { data: me } = useMeQuery()
  const schema = useMemo(() => inviteSchema(t), [t])
  const mutation = useCreateInviteMutation()
  const [createdLink, setCreatedLink] = useState<string | null>(null)

  const form = useForm<InviteFormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      target: 'project',
      email: '',
      projectId: me?.projects[0]?.id ?? '',
      projectRole: 'member',
    },
  })
  const target = form.watch('target')
  const errorMessage = authErrorMessage(mutation.error, t)

  const close = (next: boolean) => {
    if (!next) {
      form.reset()
      mutation.reset()
      setCreatedLink(null)
    }
    onOpenChange(next)
  }

  const onSubmit = form.handleSubmit((values) => {
    const body =
      values.target === 'tenantAdmin'
        ? { email: values.email, tenantRole: 'admin' as const }
        : { email: values.email, projectId: values.projectId, projectRole: values.projectRole }
    mutation.mutate(body, {
      onSuccess: (created) => {
        setCreatedLink(`${window.location.origin}${paths.invite(created.token)}`)
      },
    })
  })

  const copyLink = async () => {
    if (!createdLink) return
    await navigator.clipboard.writeText(createdLink)
    toast.success(t('settings:invite.linkCopied'))
  }

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('settings:invite.title')}</DialogTitle>
          <DialogDescription>{t('settings:invite.description')}</DialogDescription>
        </DialogHeader>
        {createdLink ? (
          <div className="space-y-4">
            <p className="text-sm text-text-secondary">{t('settings:invite.created')}</p>
            <div className="flex items-center gap-2">
              <Input readOnly value={createdLink} onFocus={(event) => event.currentTarget.select()} />
              <Button variant="outline" size="icon" onClick={() => void copyLink()} aria-label={t('actions.copy')}>
                <Copy className="size-4" />
              </Button>
            </div>
            <DialogFooter>
              <Button onClick={() => close(false)}>{t('actions.done')}</Button>
            </DialogFooter>
          </div>
        ) : (
          <Form {...form}>
            <form onSubmit={(event) => void onSubmit(event)} className="space-y-4" noValidate>
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('auth:fields.email')}</FormLabel>
                    <FormControl>
                      <Input type="email" autoComplete="off" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="target"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('settings:invite.target')}</FormLabel>
                    <FormControl>
                      <select className={cn(selectClassName)} {...field}>
                        <option value="project">{t('settings:invite.targetProject')}</option>
                        <option value="tenantAdmin">{t('settings:invite.targetTenantAdmin')}</option>
                      </select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              {target === 'project' ? (
                <>
                  <FormField
                    control={form.control}
                    name="projectId"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('settings:invite.project')}</FormLabel>
                        <FormControl>
                          <select className={cn(selectClassName)} {...field}>
                            {(me?.projects ?? []).map((project) => (
                              <option key={project.id} value={project.id}>
                                {project.name}
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
                    name="projectRole"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('settings:invite.role')}</FormLabel>
                        <FormControl>
                          <select className={cn(selectClassName)} {...field}>
                            <option value="member">{t('settings:invite.roles.member')}</option>
                            <option value="viewer">{t('settings:invite.roles.viewer')}</option>
                            <option value="project_admin">{t('settings:invite.roles.project_admin')}</option>
                          </select>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </>
              ) : null}
              {errorMessage ? <p className="text-sm text-status-error">{errorMessage}</p> : null}
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => close(false)}>
                  {t('actions.cancel')}
                </Button>
                <Button type="submit" disabled={mutation.isPending}>
                  {t('settings:invite.submit')}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        )}
      </DialogContent>
    </Dialog>
  )
}
