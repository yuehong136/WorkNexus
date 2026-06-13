import { isAPIError } from '@/lib/api-client'
import type { AppTFunction } from '@/locales/i18n'

const PROJECT_ERROR_KEYS = {
  5001: 'projects:errors.keyExists',
} as const

export function projectErrorMessage(error: unknown, t: AppTFunction): string | null {
  if (!error) return null
  if (isAPIError(error)) {
    const key = PROJECT_ERROR_KEYS[error.code as keyof typeof PROJECT_ERROR_KEYS]
    if (key) return t(key)
  }
  return t('errors.requestFailed')
}
