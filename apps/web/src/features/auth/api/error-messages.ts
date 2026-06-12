import { isAPIError } from '@/lib/api-client'
import type { AppTFunction } from '@/locales/i18n'

const AUTH_ERROR_KEYS = {
  4002: 'auth:errors.invalidCredentials',
  4003: 'auth:errors.userDisabled',
  4004: 'auth:errors.emailExists',
  4005: 'auth:errors.inviteNotFound',
  4006: 'auth:errors.inviteExpired',
  4007: 'auth:errors.inviteAccepted',
  4008: 'auth:errors.inviteRevoked',
  4012: 'auth:errors.passwordTooWeak',
} as const

export function authErrorMessage(error: unknown, t: AppTFunction): string | null {
  if (!error) return null
  if (isAPIError(error)) {
    const key = AUTH_ERROR_KEYS[error.code as keyof typeof AUTH_ERROR_KEYS]
    if (key) return t(key)
  }
  return t('errors.requestFailed')
}
