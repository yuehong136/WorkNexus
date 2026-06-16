import i18next, { type TFunction } from 'i18next'
import { initReactI18next } from 'react-i18next'

/** t() signature covering every namespace — for helpers that take t as a parameter. */
export type AppTFunction = TFunction<
  ['common', 'auth', 'settings', 'projects', 'workItems', 'intake', 'dashboard', 'skills', 'workchat', 'audit']
>

import { DEFAULT_LOCALE, localeRegistry, type ProductLocale } from './locale-registry'

const loaded = new Set<ProductLocale>()

export async function loadLocale(locale: ProductLocale): Promise<void> {
  if (loaded.has(locale)) return
  const resources = (await localeRegistry[locale].load()).default
  for (const [ns, bundle] of Object.entries(resources)) {
    i18next.addResourceBundle(locale, ns, bundle, true, true)
  }
  loaded.add(locale)
}

export async function initI18n(initialLocale: ProductLocale = DEFAULT_LOCALE): Promise<void> {
  await i18next.use(initReactI18next).init({
    lng: initialLocale,
    fallbackLng: DEFAULT_LOCALE,
    defaultNS: 'common',
    ns: ['common', 'auth', 'settings', 'projects', 'workItems', 'intake', 'dashboard', 'skills', 'workchat'],
    resources: {},
    interpolation: { escapeValue: false },
  })
  await loadLocale(initialLocale)
}

export async function changeLocale(locale: ProductLocale): Promise<void> {
  await loadLocale(locale)
  await i18next.changeLanguage(locale)
}

export default i18next
