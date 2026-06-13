import { Languages, Moon, Sun, SunMoon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { NavLink, Outlet } from 'react-router'

import { Button } from '@/components/ui/button'
import { UserMenu } from '@/features/auth/components/user-menu'
import { PermissionGate } from '@/lib/auth/permission-gate'
import { paths } from '@/lib/paths'
import { cn } from '@/lib/utils'
import { type Theme, useUIStore } from '@/stores/ui'

const themeOrder: Theme[] = ['light', 'dark', 'system']

const themeIcons = {
  light: Sun,
  dark: Moon,
  system: SunMoon,
} as const

function ThemeToggle() {
  const { t } = useTranslation()
  const theme = useUIStore((s) => s.theme)
  const setTheme = useUIStore((s) => s.setTheme)
  const Icon = themeIcons[theme]

  const cycle = () => {
    const next = themeOrder[(themeOrder.indexOf(theme) + 1) % themeOrder.length]
    setTheme(next)
  }

  return (
    <Button variant="ghost" size="icon" onClick={cycle} aria-label={t('theme.toggle')} title={t(`theme.${theme}`)}>
      <Icon className="size-4" />
    </Button>
  )
}

function LanguageToggle() {
  const { t } = useTranslation()
  const language = useUIStore((s) => s.language)
  const setLanguage = useUIStore((s) => s.setLanguage)

  const toggle = () => {
    void setLanguage(language === 'zh-CN' ? 'en-US' : 'zh-CN')
  }

  return (
    <Button variant="ghost" size="icon" onClick={toggle} aria-label={t('language.label')}>
      <Languages className="size-4" />
    </Button>
  )
}

const navLinkClassName = ({ isActive }: { isActive: boolean }) =>
  cn(
    'block rounded-md px-3 py-2 text-sm text-text-secondary hover:bg-surface-secondary',
    isActive && 'bg-surface-secondary font-medium text-text-primary',
  )

export function AppShell() {
  const { t } = useTranslation()

  return (
    <div className="flex h-screen">
      <aside className="flex w-56 flex-col border-r border-border-default bg-surface-primary">
        <div className="flex h-14 items-center gap-2 border-b border-border-default px-4">
          <span className="text-base font-semibold text-text-primary">{t('app.name')}</span>
          <span className="text-xs text-text-muted">{t('app.tagline')}</span>
        </div>
        <nav className="flex-1 space-y-1 p-2">
          <NavLink to={paths.home()} end className={navLinkClassName}>
            {t('nav.home')}
          </NavLink>
          <PermissionGate permission="project.read">
            <NavLink to={paths.projects()} className={navLinkClassName}>
              {t('nav.projects')}
            </NavLink>
          </PermissionGate>
          <PermissionGate permission="user.read">
            <NavLink to={paths.settingsMembers()} className={navLinkClassName}>
              {t('nav.members')}
            </NavLink>
          </PermissionGate>
        </nav>
      </aside>
      <div className="flex flex-1 flex-col">
        <header className="flex h-14 items-center justify-end gap-1 border-b border-border-default bg-surface-primary px-4">
          <LanguageToggle />
          <ThemeToggle />
          <UserMenu />
        </header>
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
