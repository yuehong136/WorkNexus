import { useTranslation } from 'react-i18next'
import { NavLink, Outlet } from 'react-router'

import { PermissionGate } from '@/lib/auth/permission-gate'
import { paths } from '@/lib/paths'
import { cn } from '@/lib/utils'

const subNavClassName = ({ isActive }: { isActive: boolean }) =>
  cn(
    'block rounded-md px-3 py-2 text-sm text-text-secondary hover:bg-surface-secondary',
    isActive && 'bg-surface-secondary font-medium text-text-primary',
  )

export function SettingsLayout() {
  const { t } = useTranslation('settings')
  return (
    <div className="flex gap-8">
      <aside className="w-48 shrink-0 space-y-1">
        <h1 className="px-3 pb-2 text-lg font-semibold text-text-primary">{t('title')}</h1>
        <NavLink to={paths.settingsProfile()} className={subNavClassName}>
          {t('nav.profile')}
        </NavLink>
        <PermissionGate permission="project.read">
          <NavLink to={paths.settingsProjects()} className={subNavClassName}>
            {t('nav.projects')}
          </NavLink>
        </PermissionGate>
        <PermissionGate permission="ai_agent.manage">
          <NavLink to={paths.settingsAi()} className={subNavClassName}>
            {t('nav.ai')}
          </NavLink>
        </PermissionGate>
        <PermissionGate permission="skill.read">
          <NavLink to={paths.settingsSkills()} className={subNavClassName}>
            {t('nav.skills')}
          </NavLink>
        </PermissionGate>
        <PermissionGate permission="user.read">
          <NavLink to={paths.settingsMembers()} className={subNavClassName}>
            {t('nav.members')}
          </NavLink>
        </PermissionGate>
      </aside>
      <div className="min-w-0 flex-1">
        <Outlet />
      </div>
    </div>
  )
}
