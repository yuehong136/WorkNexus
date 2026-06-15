import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router'

import { EmptyState } from '@/components/patterns/empty-state'
import { ErrorState } from '@/components/patterns/error-state'
import { PageSkeleton } from '@/components/patterns/page-skeleton'
import { DashboardCards } from '@/features/dashboard/components/dashboard-cards'
import { DistributionCharts } from '@/features/dashboard/components/distribution-charts'
import { InsightsPanel } from '@/features/dashboard/components/insights-panel'
import { OverdueTable } from '@/features/dashboard/components/overdue-table'
import { TrendChart } from '@/features/dashboard/components/trend-chart'
import { WorkloadTable } from '@/features/dashboard/components/workload-table'
import { useDashboardSummaryQuery } from '@/features/dashboard/api/use-dashboard-summary-query'
import { useDashboardWorkloadQuery } from '@/features/dashboard/api/use-dashboard-workload-query'
import { paths } from '@/lib/paths'

export function DashboardPage() {
  const { t } = useTranslation('dashboard')
  const { projectId = '' } = useParams()
  const summaryQuery = useDashboardSummaryQuery(projectId)
  const workloadQuery = useDashboardWorkloadQuery(projectId)

  if (summaryQuery.isPending) return <PageSkeleton />
  if (summaryQuery.isError) return <ErrorState onRetry={() => void summaryQuery.refetch()} />

  const summary = summaryQuery.data

  return (
    <div className="space-y-6">
      <Link to={paths.projectDetail(projectId)} className="text-sm text-text-muted hover:underline">
        ← {t('backToProject')}
      </Link>

      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t('title')}</h1>
        <p className="text-sm text-text-muted">{t('description')}</p>
      </div>

      {summary.totalCount === 0 ? (
        <EmptyState description={t('empty')} />
      ) : (
        <>
          <DashboardCards summary={summary} />
          <DistributionCharts summary={summary} />
          <TrendChart summary={summary} />
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {workloadQuery.isError ? (
              <ErrorState onRetry={() => void workloadQuery.refetch()} />
            ) : (
              <WorkloadTable items={workloadQuery.data?.items ?? []} />
            )}
            <InsightsPanel projectId={projectId} />
          </div>
          <OverdueTable projectId={projectId} />
        </>
      )}
    </div>
  )
}
