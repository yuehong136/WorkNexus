import type { RiskLevel } from '@worknexus/contracts'
import { useTranslation } from 'react-i18next'

import { EmptyState } from '@/components/patterns/empty-state'
import { ErrorState } from '@/components/patterns/error-state'
import { PageSkeleton } from '@/components/patterns/page-skeleton'
import { Badge } from '@/components/ui/badge'
import { useSkillCatalogQuery } from '@/features/settings/api/use-skill-catalog-query'

const riskVariant: Record<RiskLevel, 'secondary' | 'warning' | 'error'> = {
  read: 'secondary',
  low_write: 'warning',
  high_write: 'error',
}

export function SkillsSettingsPage() {
  const { t } = useTranslation('settings')
  const query = useSkillCatalogQuery()

  if (query.isPending) return <PageSkeleton />
  if (query.isError) return <ErrorState onRetry={() => void query.refetch()} />

  const skills = query.data
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-text-primary">{t('skills.title')}</h2>
        <p className="text-sm text-text-muted">{t('skills.description')}</p>
      </div>

      {skills.length === 0 ? (
        <EmptyState description={t('skills.empty')} />
      ) : (
        <div className="space-y-4">
          {skills.map((skill) => (
            <div key={skill.skillCode} className="rounded-lg border border-border-default bg-surface-primary p-4">
              <h3 className="font-mono text-sm font-semibold text-text-primary">{skill.skillCode}</h3>
              <ul className="mt-3 space-y-2">
                {skill.tools.map((tool) => (
                  <li key={tool.toolName} className="flex items-center justify-between gap-2">
                    <span className="font-mono text-xs text-text-secondary">{tool.toolName}</span>
                    {tool.riskLevel ? (
                      <div className="flex items-center gap-2">
                        <Badge variant={riskVariant[tool.riskLevel]}>{t(`skills.risk.${tool.riskLevel}`)}</Badge>
                        <span className="text-xs text-text-muted">{t(`skills.policy.${tool.riskLevel}`)}</span>
                      </div>
                    ) : (
                      <span className="text-text-muted">—</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
