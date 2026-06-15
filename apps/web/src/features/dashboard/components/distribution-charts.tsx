import type { DashboardSummaryOut } from '@worknexus/contracts'
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import { BarChart } from '@/components/patterns/charts/bar-chart'
import type { CategoryDatum } from '@/components/patterns/charts/chart-primitives'
import { DonutChart } from '@/components/patterns/charts/donut-chart'
import { useChartColors } from '@/lib/chart-colors'

const STATUSES = ['backlog', 'todo', 'in_progress', 'review', 'done', 'cancelled'] as const
const TYPES = ['task', 'requirement', 'bug', 'risk', 'decision', 'approval', 'incident', 'feedback'] as const
const PRIORITIES = ['low', 'medium', 'high', 'urgent'] as const
const SOURCES = ['manual', 'ai_chat', 'intake', 'mcp', 'api'] as const

function ChartCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="space-y-3 rounded-lg border border-border-default bg-surface-primary p-4">
      <h3 className="text-sm font-medium text-text-secondary">{title}</h3>
      {children}
    </div>
  )
}

export function DistributionCharts({ summary }: { summary: DashboardSummaryOut }) {
  const { t } = useTranslation(['dashboard', 'workItems'])
  const colors = useChartColors()

  const build = <T extends string>(
    values: readonly T[],
    counts: Record<string, number>,
    label: (v: T) => string,
  ): CategoryDatum[] =>
    values.map((value, index) => ({
      label: label(value),
      value: counts[value] ?? 0,
      color: colors.at(index),
    }))

  const statusData = build(STATUSES, summary.statusCounts, (v) => t(`workItems:status.${v}`))
  const typeData = build(TYPES, summary.typeCounts, (v) => t(`workItems:type.${v}`))
  const priorityData = build(PRIORITIES, summary.priorityCounts, (v) => t(`workItems:priority.${v}`))
  const sourceData = build(SOURCES, summary.sourceCounts, (v) => t(`workItems:source.${v}`))
  const axis = colors.token('text-muted')

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <ChartCard title={t('dashboard:distribution.status')}>
        <DonutChart data={statusData} />
      </ChartCard>
      <ChartCard title={t('dashboard:distribution.type')}>
        <BarChart data={typeData} axisColor={axis} />
      </ChartCard>
      <ChartCard title={t('dashboard:distribution.priority')}>
        <BarChart data={priorityData} axisColor={axis} />
      </ChartCard>
      <ChartCard title={t('dashboard:distribution.source')}>
        <BarChart data={sourceData} axisColor={axis} />
      </ChartCard>
    </div>
  )
}
