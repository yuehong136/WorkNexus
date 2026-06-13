import { useTranslation } from 'react-i18next'

import { Skeleton } from '@/components/ui/skeleton'
import { useProjectSummaryQuery } from '@/features/projects/api/use-project-summary-query'
import { formatDateTime } from '@/lib/datetime'

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-border-default bg-surface-primary p-4">
      <div className="text-2xl font-semibold text-text-primary">{value}</div>
      <div className="text-xs text-text-muted">{label}</div>
    </div>
  )
}

export function ProjectSummaryCards({ projectId }: { projectId: string }) {
  const { t } = useTranslation('projects')
  const query = useProjectSummaryQuery(projectId)

  if (query.isPending) return <Skeleton className="h-24 w-full" />
  if (query.isError) return null

  const summary = query.data
  return (
    <section className="space-y-3">
      <h2 className="text-sm font-medium text-text-secondary">{t('summary.title')}</h2>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label={t('summary.total')} value={summary.totalCount} />
        <StatCard label={t('summary.highPriority')} value={summary.highPriorityCount} />
        <StatCard label={t('summary.overdue')} value={summary.overdueCount} />
        <StatCard label={t('summary.aiCreated')} value={summary.aiCreatedCount} />
      </div>
      <div className="rounded-lg border border-border-default bg-surface-primary p-4">
        <div className="mb-2 text-xs text-text-muted">{t('summary.recentActivity')}</div>
        {summary.recentActivities.length === 0 ? (
          <p className="text-sm text-text-muted">{t('summary.noActivity')}</p>
        ) : (
          <ul className="space-y-1">
            {summary.recentActivities.map((activity) => (
              <li key={activity.id} className="flex items-center justify-between gap-2 text-sm">
                <span className="truncate text-text-primary">
                  <span className="font-mono text-xs text-text-secondary">{activity.workItemKey}</span>{' '}
                  {activity.workItemTitle}
                </span>
                <span className="shrink-0 text-xs text-text-muted">{formatDateTime(activity.createdAt)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}
