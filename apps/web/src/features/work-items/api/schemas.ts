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

// Fixed state machine (mirrors the backend ALLOWED_TRANSITIONS).
type WorkItemStatusValue = (typeof WORK_ITEM_STATUSES)[number]

export const ALLOWED_TRANSITIONS: Record<WorkItemStatusValue, readonly WorkItemStatusValue[]> = {
  backlog: ['todo', 'cancelled'],
  todo: ['in_progress', 'cancelled'],
  in_progress: ['review', 'cancelled'],
  review: ['done', 'in_progress', 'cancelled'],
  done: [],
  cancelled: [],
}

export const MANUAL_RELATION_TYPES = ['parent_child', 'blocks', 'relates_to', 'duplicates'] as const

// Type-specific custom fields (mirrors the backend CUSTOM_FIELD_SCHEMAS, decision B).
export const CUSTOM_FIELDS_BY_TYPE = {
  task: [],
  requirement: ['business_goal', 'user_value', 'boundary_conditions', 'dependencies'],
  bug: ['severity', 'steps_to_reproduce', 'expected_result', 'actual_result', 'environment', 'affected_version'],
  risk: ['risk_level', 'impact', 'probability', 'mitigation_plan', 'trigger_condition'],
  decision: ['background', 'options', 'decision_result', 'decision_owner', 'impact_scope'],
  approval: ['approval_type', 'approvers', 'approval_status', 'approval_comment'],
  incident: [],
  feedback: [],
} as const satisfies Record<(typeof WORK_ITEM_TYPES)[number], readonly string[]>

export type CustomFieldKey = (typeof CUSTOM_FIELDS_BY_TYPE)[keyof typeof CUSTOM_FIELDS_BY_TYPE][number]

export function workItemCreateSchema(t: AppTFunction) {
  return z.object({
    type: z.enum(WORK_ITEM_TYPES),
    title: z.string().min(1, t('workItems:form.titleRequired')).max(300),
    description: z.string().max(20000).optional(),
    priority: z.enum(WORK_ITEM_PRIORITIES),
  })
}

export type WorkItemCreateValues = z.infer<ReturnType<typeof workItemCreateSchema>>

export function workItemEditSchema(t: AppTFunction) {
  return z.object({
    title: z.string().min(1, t('workItems:form.titleRequired')).max(300),
    description: z.string().max(20000).optional(),
    priority: z.enum(WORK_ITEM_PRIORITIES),
    assigneeId: z.string(),
    acceptanceCriteria: z.string().max(20000).optional(),
  })
}

export type WorkItemEditValues = z.infer<ReturnType<typeof workItemEditSchema>>
