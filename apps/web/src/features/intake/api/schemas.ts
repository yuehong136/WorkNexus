import { z } from 'zod'

import type { AppTFunction } from '@/locales/i18n'

export const INTAKE_STATUSES = [
  'new',
  'triaging',
  'rejected',
  'duplicate',
  'snoozed',
  'converted',
] as const

export const INTAKE_SOURCES = ['manual', 'ai_chat', 'api', 'mcp'] as const

// Work item type/priority value lists for the convert form. Mirrors the backend enums;
// features cannot import each other, so the intake convert form keeps its own copy and
// reuses the workItems namespace only for the human labels.
export const CONVERT_TYPES = [
  'task',
  'requirement',
  'bug',
  'risk',
  'decision',
  'approval',
  'incident',
  'feedback',
] as const

export const CONVERT_PRIORITIES = ['low', 'medium', 'high', 'urgent'] as const

export function intakeCreateSchema(t: AppTFunction) {
  return z.object({
    title: z.string().min(1, t('intake:form.titleRequired')).max(300),
    description: z.string().max(20000).optional(),
  })
}

export type IntakeCreateValues = z.infer<ReturnType<typeof intakeCreateSchema>>

export function intakeConvertSchema(t: AppTFunction) {
  return z.object({
    type: z.enum(CONVERT_TYPES),
    title: z.string().min(1, t('intake:form.titleRequired')).max(300),
    priority: z.enum(CONVERT_PRIORITIES),
    assigneeId: z.string(),
  })
}

export type IntakeConvertValues = z.infer<ReturnType<typeof intakeConvertSchema>>
