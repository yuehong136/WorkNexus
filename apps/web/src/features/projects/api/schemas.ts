import { z } from 'zod'

import type { AppTFunction } from '@/locales/i18n'

export function projectCreateSchema(t: AppTFunction) {
  return z.object({
    name: z.string().min(1, t('projects:form.nameRequired')).max(200),
    key: z.string().regex(/^[A-Za-z0-9]{2,10}$/, t('projects:form.keyInvalid')),
    description: z.string().max(2000).optional(),
  })
}

export type ProjectCreateValues = z.infer<ReturnType<typeof projectCreateSchema>>

export function projectEditSchema(t: AppTFunction) {
  return z.object({
    name: z.string().min(1, t('projects:form.nameRequired')).max(200),
    description: z.string().max(2000).optional(),
  })
}

export type ProjectEditValues = z.infer<ReturnType<typeof projectEditSchema>>

export function memberAddSchema(t: AppTFunction) {
  return z.object({
    userId: z.string().min(1, t('projects:members.userRequired')),
    role: z.enum(['project_admin', 'member', 'viewer']),
  })
}

export type MemberAddValues = z.infer<ReturnType<typeof memberAddSchema>>
