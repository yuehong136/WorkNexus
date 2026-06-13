import { isAPIError } from '@/lib/api-client'
import type { AppTFunction } from '@/locales/i18n'

const WORK_ITEM_ERROR_KEYS = {
  2002: 'workItems:errors.invalidTransition',
  2005: 'workItems:errors.invalidRelation',
  2006: 'workItems:errors.relationExists',
  2007: 'workItems:errors.invalidCustomFields',
  2008: 'workItems:errors.invalidAssignee',
  2009: 'workItems:errors.projectArchived',
} as const

export function workItemErrorMessage(error: unknown, t: AppTFunction): string | null {
  if (!error) return null
  if (isAPIError(error)) {
    const key = WORK_ITEM_ERROR_KEYS[error.code as keyof typeof WORK_ITEM_ERROR_KEYS]
    if (key) return t(key)
  }
  return t('errors.requestFailed')
}
