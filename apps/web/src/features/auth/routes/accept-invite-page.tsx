import { zodResolver } from '@hookform/resolvers/zod'
import { useMemo } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router'

import { ErrorState } from '@/components/patterns/error-state'
import { PageSkeleton } from '@/components/patterns/page-skeleton'
import { Button } from '@/components/ui/button'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { authErrorMessage } from '@/features/auth/api/error-messages'
import { acceptInviteSchema, type AcceptInviteFormValues } from '@/features/auth/api/schemas'
import { useAcceptInviteMutation } from '@/features/auth/api/use-accept-invite-mutation'
import { useInvitePreviewQuery } from '@/features/auth/api/use-invite-preview-query'
import { AuthCard } from '@/features/auth/components/auth-card'
import { paths } from '@/lib/paths'

export function AcceptInvitePage() {
  const { token = '' } = useParams()
  const { t } = useTranslation(['common', 'auth', 'settings'])
  const navigate = useNavigate()
  const preview = useInvitePreviewQuery(token)
  const schema = useMemo(() => acceptInviteSchema(t), [t])
  const form = useForm<AcceptInviteFormValues>({
    resolver: zodResolver(schema),
    defaultValues: { displayName: '', password: '', confirmPassword: '' },
  })
  const mutation = useAcceptInviteMutation(token)
  const errorMessage = authErrorMessage(mutation.error, t)

  if (preview.isPending) return <PageSkeleton />
  if (preview.isError) {
    return (
      <AuthCard title={t('auth:invite.title')}>
        <ErrorState message={authErrorMessage(preview.error, t) ?? undefined} />
      </AuthCard>
    )
  }
  if (preview.data.status !== 'pending') {
    return (
      <AuthCard title={t('auth:invite.title')}>
        <p className="text-sm text-text-secondary">{t(`auth:invite.status.${preview.data.status}`)}</p>
      </AuthCard>
    )
  }

  const onSubmit = form.handleSubmit((values) => {
    mutation.mutate(
      { displayName: values.displayName, password: values.password },
      { onSuccess: () => void navigate(paths.home(), { replace: true }) },
    )
  })

  return (
    <AuthCard title={t('auth:invite.title')} description={t('auth:invite.subtitle', { email: preview.data.email })}>
      <Form {...form}>
        <form onSubmit={(event) => void onSubmit(event)} className="space-y-4" noValidate>
          <FormField
            control={form.control}
            name="displayName"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('auth:fields.displayName')}</FormLabel>
                <FormControl>
                  <Input type="text" autoComplete="name" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="password"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('auth:fields.password')}</FormLabel>
                <FormControl>
                  <Input type="password" autoComplete="new-password" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="confirmPassword"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('auth:fields.confirmPassword')}</FormLabel>
                <FormControl>
                  <Input type="password" autoComplete="new-password" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          {errorMessage ? <p className="text-sm text-status-error">{errorMessage}</p> : null}
          <Button type="submit" className="w-full" disabled={mutation.isPending}>
            {t('auth:invite.submit')}
          </Button>
        </form>
      </Form>
    </AuthCard>
  )
}
