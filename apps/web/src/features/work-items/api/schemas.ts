import { z } from 'zod'

import type { AppTFunction } from '@/locales/i18n'

export const WORK_ITEM_TYPES = [
  'task',
  'requirement',
  'bug',
  'risk',
  'decision',
  'approval',
  'incident',
  'feedback',
] as const

export const WORK_ITEM_PRIORITIES = ['low', 'medium', 'high', 'urgent'] as const

export const WORK_ITEM_STATUSES = ['backlog', 'todo', 'in_progress', 'review', 'done', 'cancelled'] as const

export function workItemCreateSchema(t: AppTFunction) {
  return z.object({
    type: z.enum(WORK_ITEM_TYPES),
    title: z.string().min(1, t('workItems:form.titleRequired')).max(300),
    description: z.string().max(20000).optional(),
    priority: z.enum(WORK_ITEM_PRIORITIES),
  })
}

export type WorkItemCreateValues = z.infer<ReturnType<typeof workItemCreateSchema>>
