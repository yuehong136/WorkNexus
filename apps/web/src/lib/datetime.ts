import { format, parseISO } from 'date-fns'
import { enUS, zhCN } from 'date-fns/locale'

import i18n from '@/locales/i18n'
import type { ProductLocale } from '@/locales/locale-registry'

const dateFnsLocales = {
  'zh-CN': zhCN,
  'en-US': enUS,
} as const

function currentLocale() {
  return dateFnsLocales[i18n.language as ProductLocale] ?? zhCN
}

export function formatDateTime(value: string | Date | null | undefined): string {
  if (!value) return '-'
  const date = typeof value === 'string' ? parseISO(value) : value
  return format(date, 'yyyy-MM-dd HH:mm', { locale: currentLocale() })
}

export function formatDate(value: string | Date | null | undefined): string {
  if (!value) return '-'
  const date = typeof value === 'string' ? parseISO(value) : value
  return format(date, 'yyyy-MM-dd', { locale: currentLocale() })
}
