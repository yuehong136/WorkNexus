import { isAPIError } from '@/lib/api-client'
import type { AppTFunction } from '@/locales/i18n'

const INTAKE_ERROR_KEYS = {
  3001: 'intake:errors.notFound',
  3002: 'intake:errors.notActionable',
  3003: 'intake:errors.duplicateTargetInvalid',
} as const

export function intakeErrorMessage(error: unknown, t: AppTFunction): string | null {
  if (!error) return null
  if (isAPIError(error)) {
    const key = INTAKE_ERROR_KEYS[error.code as keyof typeof INTAKE_ERROR_KEYS]
    if (key) return t(key)
  }
  return t('errors.requestFailed')
}
