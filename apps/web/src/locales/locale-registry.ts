export const localeRegistry = {
  'zh-CN': {
    nativeLabel: '简体中文',
    load: () => import('./zh-CN'),
  },
  'en-US': {
    nativeLabel: 'English',
    load: () => import('./en-US'),
  },
} as const

export type ProductLocale = keyof typeof localeRegistry

export const DEFAULT_LOCALE: ProductLocale = 'zh-CN'

export function isProductLocale(value: string): value is ProductLocale {
  return value in localeRegistry
}
