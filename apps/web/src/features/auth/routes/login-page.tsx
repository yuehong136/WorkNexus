import { zodResolver } from '@hookform/resolvers/zod'
import { useMemo } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { authErrorMessage } from '@/features/auth/api/error-messages'
import { loginSchema, type LoginFormValues } from '@/features/auth/api/schemas'
import { useLoginMutation } from '@/features/auth/api/use-login-mutation'
import { AuthCard } from '@/features/auth/components/auth-card'

export function LoginPage() {
  const { t } = useTranslation(['common', 'auth', 'settings'])
  const schema = useMemo(() => loginSchema(t), [t])
  const form = useForm<LoginFormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: '', password: '' },
  })
  const mutation = useLoginMutation()
  const errorMessage = authErrorMessage(mutation.error, t)

  const onSubmit = form.handleSubmit((values) => mutation.mutate(values))

  return (
    <AuthCard title={t('auth:login.title')} description={t('auth:login.subtitle')}>
      <Form {...form}>
        <form onSubmit={(event) => void onSubmit(event)} className="space-y-4" noValidate>
          <FormField
            control={form.control}
            name="email"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('auth:fields.email')}</FormLabel>
                <FormControl>
                  <Input type="email" autoComplete="email" {...field} />
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
                  <Input type="password" autoComplete="current-password" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          {errorMessage ? <p className="text-sm text-status-error">{errorMessage}</p> : null}
          <Button type="submit" className="w-full" disabled={mutation.isPending}>
            {t('auth:login.submit')}
          </Button>
        </form>
      </Form>
    </AuthCard>
  )
}
