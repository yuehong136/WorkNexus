import { zodResolver } from '@hookform/resolvers/zod'
import { useMemo } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

import { ErrorState } from '@/components/patterns/error-state'
import { PageSkeleton } from '@/components/patterns/page-skeleton'
import { Button } from '@/components/ui/button'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { profileSchema, type ProfileFormValues } from '@/features/settings/api/schemas'
import { useUpdateProfileMutation } from '@/features/settings/api/use-update-profile-mutation'
import { useMeQuery } from '@/lib/auth/use-me-query'

function ReadOnlyField({ label, value }: { label: string; value: string }) {
  return (
    <div className="space-y-1">
      <p className="text-xs font-medium text-text-muted">{label}</p>
      <p className="text-sm text-text-primary">{value}</p>
    </div>
  )
}

export function ProfilePage() {
  const { t } = useTranslation(['common', 'settings'])
  const meQuery = useMeQuery()
  const mutation = useUpdateProfileMutation()
  const schema = useMemo(() => profileSchema(t), [t])
  const form = useForm<ProfileFormValues>({
    resolver: zodResolver(schema),
    values: { displayName: meQuery.data?.user.displayName ?? '' },
  })

  if (meQuery.isPending) return <PageSkeleton />
  if (meQuery.isError) return <ErrorState onRetry={() => void meQuery.refetch()} />

  const me = meQuery.data
  const onSubmit = form.handleSubmit((values) => {
    mutation.mutate(
      { displayName: values.displayName },
      { onSuccess: () => toast.success(t('settings:profile.saved')) },
    )
  })

  return (
    <div className="max-w-lg space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-text-primary">{t('settings:profile.title')}</h2>
        <p className="text-sm text-text-muted">{t('settings:profile.description')}</p>
      </div>

      <Form {...form}>
        <form onSubmit={(event) => void onSubmit(event)} className="space-y-4" noValidate>
          <FormField
            control={form.control}
            name="displayName"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('settings:profile.displayName')}</FormLabel>
                <FormControl>
                  <Input autoComplete="off" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <Button type="submit" disabled={mutation.isPending}>
            {t('settings:profile.save')}
          </Button>
        </form>
      </Form>

      <div className="grid grid-cols-2 gap-4 border-t border-border-default pt-6">
        <ReadOnlyField label={t('settings:profile.email')} value={me.user.email} />
        <ReadOnlyField label={t('settings:profile.role')} value={me.roles.join(', ')} />
        <ReadOnlyField label={t('settings:profile.identityProvider')} value={me.user.identityProvider} />
      </div>
    </div>
  )
}
