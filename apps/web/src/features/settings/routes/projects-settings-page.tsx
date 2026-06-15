import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { EmptyState } from '@/components/patterns/empty-state'
import { Badge } from '@/components/ui/badge'
import { useMeQuery } from '@/lib/auth/use-me-query'
import { paths } from '@/lib/paths'

export function ProjectsSettingsPage() {
  const { t } = useTranslation(['common', 'settings'])
  const { data: me } = useMeQuery()
  const projects = me?.projects ?? []

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-text-primary">{t('settings:projects.title')}</h2>
        <p className="text-sm text-text-muted">{t('settings:projects.description')}</p>
      </div>

      {projects.length === 0 ? (
        <EmptyState description={t('settings:projects.empty')} />
      ) : (
        <ul className="space-y-2">
          {projects.map((project) => (
            <li
              key={project.id}
              className="flex items-center justify-between rounded-lg border border-border-default bg-surface-primary p-3"
            >
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-text-primary">{project.name}</span>
                <Badge variant="secondary">{t(`settings:invite.roles.${project.role}`)}</Badge>
              </div>
              <Link
                to={paths.projectDetail(project.id)}
                className="text-sm text-brand-primary hover:underline"
              >
                {t('settings:projects.open')}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
