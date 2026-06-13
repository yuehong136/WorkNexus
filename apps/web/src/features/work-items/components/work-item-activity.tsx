import { useTranslation } from 'react-i18next'

import { useWorkItemActivitiesQuery } from '@/features/work-items/api/use-work-item-activities-query'
import { formatDateTime } from '@/lib/datetime'

export function WorkItemActivity({ workItemId }: { workItemId: string }) {
  const { t } = useTranslation('workItems')
  const query = useWorkItemActivitiesQuery(workItemId)
  const activities = query.data ?? []

  return (
    <section className="space-y-3">
      <h3 className="text-sm font-medium text-text-secondary">{t('activity.title')}</h3>
      {activities.length > 0 ? (
        <ul className="space-y-2">
          {activities.map((activity) => {
            const actor =
              activity.actor?.displayName ??
              (activity.actorType === 'ai_agent' ? t('comments.authorAi') : t('comments.authorSystem'))
            return (
              <li key={activity.id} className="flex items-start justify-between gap-2 text-sm">
                <span className="text-text-secondary">
                  <span className="text-text-primary">{actor}</span> {t(`activityAction.${activity.action}`)}
                </span>
                <span className="shrink-0 text-xs text-text-muted">{formatDateTime(activity.createdAt)}</span>
              </li>
            )
          })}
        </ul>
      ) : (
        <p className="text-sm text-text-muted">{t('activity.empty')}</p>
      )}
    </section>
  )
}
