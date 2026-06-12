import { create } from 'zustand'
import { persist } from 'zustand/middleware'

import { changeLocale } from '@/locales/i18n'
import { DEFAULT_LOCALE, type ProductLocale } from '@/locales/locale-registry'

export type Theme = 'light' | 'dark' | 'system'

const systemDark = () =>
  typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches

export function applyTheme(theme: Theme): void {
  const resolved = theme === 'system' ? (systemDark() ? 'dark' : 'light') : theme
  document.documentElement.setAttribute('data-theme', resolved)
}

interface UIState {
  theme: Theme
  language: ProductLocale
  setTheme: (theme: Theme) => void
  setLanguage: (language: ProductLocale) => Promise<void>
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      theme: 'system',
      language: DEFAULT_LOCALE,
      setTheme: (theme) => {
        applyTheme(theme)
        set({ theme })
      },
      setLanguage: async (language) => {
        await changeLocale(language)
        set({ language })
      },
    }),
    {
      name: 'worknexus-ui',
      partialize: (state) => ({ theme: state.theme, language: state.language }),
    },
  ),
)

export function initUIPreferences(): void {
  const { theme } = useUIStore.getState()
  applyTheme(theme)
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if (useUIStore.getState().theme === 'system') applyTheme('system')
  })
}
