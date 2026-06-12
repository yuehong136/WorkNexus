import { z } from 'zod'

import type { AppTFunction } from '@/locales/i18n'

export function inviteSchema(t: AppTFunction) {
  return z.discriminatedUnion('target', [
    z.object({
      target: z.literal('tenantAdmin'),
      email: z.email(t('auth:validation.emailInvalid')),
    }),
    z.object({
      target: z.literal('project'),
      email: z.email(t('auth:validation.emailInvalid')),
      projectId: z.string().min(1, t('settings:invite.projectRequired')),
      projectRole: z.enum(['project_admin', 'member', 'viewer']),
    }),
  ])
}

export type InviteFormValues = z.infer<ReturnType<typeof inviteSchema>>
