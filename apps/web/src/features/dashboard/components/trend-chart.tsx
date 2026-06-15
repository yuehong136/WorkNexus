import type { DashboardSummaryOut } from '@worknexus/contracts'
import { useTranslation } from 'react-i18next'

import { LineChart } from '@/components/patterns/charts/line-chart'
import { useChartColors } from '@/lib/chart-colors'

export function TrendChart({ summary }: { summary: DashboardSummaryOut }) {
  const { t } = useTranslation('dashboard')
  const colors = useChartColors()

  const data = summary.createdTrend.map((point, index) => ({
    date: point.date.slice(5), // MM-DD
    created: point.count,
    completed: summary.completedTrend[index]?.count ?? 0,
  }))

  const series = [
    { key: 'created', label: t('trend.created'), color: colors.token('brand-primary') },
    { key: 'completed', label: t('trend.completed'), color: colors.token('status-success') },
  ]

  return (
    <div className="space-y-3 rounded-lg border border-border-default bg-surface-primary p-4">
      <h3 className="text-sm font-medium text-text-secondary">{t('trend.title')}</h3>
      <LineChart
        data={data}
        xKey="date"
        series={series}
        axisColor={colors.token('text-muted')}
        gridColor={colors.token('border-default')}
      />
    </div>
  )
}
