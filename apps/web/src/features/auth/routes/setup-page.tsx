import { zodResolver } from '@hookform/resolvers/zod'
import { useMemo } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { authErrorMessage } from '@/features/auth/api/error-messages'
import { setupSchema, type SetupFormValues } from '@/features/auth/api/schemas'
import { useSetupMutation } from '@/features/auth/api/use-setup-mutation'
import { AuthCard } from '@/features/auth/components/auth-card'

export function SetupPage() {
  const { t } = useTranslation(['common', 'auth', 'settings'])
  const schema = useMemo(() => setupSchema(t), [t])
  const form = useForm<SetupFormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      workspaceName: t('auth:setup.workspaceNameDefault'),
      email: '',
      displayName: '',
      password: '',
      confirmPassword: '',
    },
  })
  const mutation = useSetupMutation()
  const errorMessage = authErrorMessage(mutation.error, t)

  const onSubmit = form.handleSubmit((values) => {
    mutation.mutate({
      workspaceName: values.workspaceName,
      email: values.email,
      displayName: values.displayName,
      password: values.password,
    })
  })

  const fields = [
    { name: 'workspaceName', label: t('auth:setup.workspaceName'), type: 'text', autoComplete: 'organization' },
    { name: 'email', label: t('auth:fields.email'), type: 'email', autoComplete: 'email' },
    { name: 'displayName', label: t('auth:fields.displayName'), type: 'text', autoComplete: 'name' },
    { name: 'password', label: t('auth:fields.password'), type: 'password', autoComplete: 'new-password' },
    {
      name: 'confirmPassword',
      label: t('auth:fields.confirmPassword'),
      type: 'password',
      autoComplete: 'new-password',
    },
  ] as const

  return (
    <AuthCard title={t('auth:setup.title')} description={t('auth:setup.subtitle')}>
      <Form {...form}>
        <form onSubmit={(event) => void onSubmit(event)} className="space-y-4" noValidate>
          {fields.map(({ name, label, type, autoComplete }) => (
            <FormField
              key={name}
              control={form.control}
              name={name}
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{label}</FormLabel>
                  <FormControl>
                    <Input type={type} autoComplete={autoComplete} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          ))}
          {errorMessage ? <p className="text-sm text-status-error">{errorMessage}</p> : null}
          <Button type="submit" className="w-full" disabled={mutation.isPending}>
            {t('auth:setup.submit')}
          </Button>
        </form>
      </Form>
    </AuthCard>
  )
}
