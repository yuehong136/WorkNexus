import { z } from 'zod'

import type { AppTFunction } from '@/locales/i18n'

export function loginSchema(t: AppTFunction) {
  return z.object({
    email: z.email(t('auth:validation.emailInvalid')),
    password: z.string().min(1, t('auth:validation.passwordRequired')),
  })
}

export type LoginFormValues = z.infer<ReturnType<typeof loginSchema>>

export function setupSchema(t: AppTFunction) {
  return z
    .object({
      workspaceName: z.string().min(1, t('auth:validation.workspaceNameRequired')),
      email: z.email(t('auth:validation.emailInvalid')),
      displayName: z.string().min(1, t('auth:validation.displayNameRequired')),
      password: z.string().min(8, t('auth:validation.passwordMin')),
      confirmPassword: z.string(),
    })
    .refine((values) => values.password === values.confirmPassword, {
      path: ['confirmPassword'],
      message: t('auth:validation.passwordMismatch'),
    })
}

export type SetupFormValues = z.infer<ReturnType<typeof setupSchema>>

export function acceptInviteSchema(t: AppTFunction) {
  return z
    .object({
      displayName: z.string().min(1, t('auth:validation.displayNameRequired')),
      password: z.string().min(8, t('auth:validation.passwordMin')),
      confirmPassword: z.string(),
    })
    .refine((values) => values.password === values.confirmPassword, {
      path: ['confirmPassword'],
      message: t('auth:validation.passwordMismatch'),
    })
}

export type AcceptInviteFormValues = z.infer<ReturnType<typeof acceptInviteSchema>>
