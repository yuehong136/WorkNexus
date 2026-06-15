import { Sparkles } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { EmptyState } from '@/components/patterns/empty-state'
import { ErrorState } from '@/components/patterns/error-state'
import { Skeleton } from '@/components/ui/skeleton'
import { useDashboardInsightsQuery } from '@/features/dashboard/api/use-dashboard-insights-query'
import { InsightCard } from '@/features/dashboard/components/insight-card'
import { formatDateTime } from '@/lib/datetime'

export function InsightsPanel({ projectId }: { projectId: string }) {
  const { t } = useTranslation('dashboard')
  const query = useDashboardInsightsQuery(projectId)

  return (
    <section className="space-y-3">
      <div className="flex items-center gap-2">
        <Sparkles className="size-4 text-text-muted" />
        <h3 className="text-sm font-medium text-text-secondary">{t('insights.title')}</h3>
      </div>
      <p className="text-xs text-text-muted">{t('insights.advisoryNote')}</p>

      {query.isPending ? (
        <Skeleton className="h-32 w-full" />
      ) : query.isError ? (
        <ErrorState onRetry={() => void query.refetch()} />
      ) : query.data.insights.length === 0 ? (
        <EmptyState icon={Sparkles} description={t('insights.empty')} />
      ) : (
        <div className="space-y-2">
          {query.data.insights.map((insight, index) => (
            <InsightCard key={`${insight.kind}-${index}`} insight={insight} />
          ))}
          <p className="text-xs text-text-muted">
            {t('insights.provenance', {
              provider: query.data.provenance.provider,
              version: query.data.provenance.version,
              time: formatDateTime(query.data.provenance.generatedAt),
            })}
          </p>
        </div>
      )}
    </section>
  )
}
