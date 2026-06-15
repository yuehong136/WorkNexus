import type { InsightOut } from '@worknexus/contracts'
import { Clock, Flame, ShieldAlert, Sparkles, Users, type LucideIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Markdown } from '@/lib/markdown'

const KIND_ICON = {
  overdue: Clock,
  high_priority: Flame,
  risk: ShieldAlert,
  workload: Users,
} as const satisfies Record<string, LucideIcon>

const SEVERITY_CLASS = {
  critical: 'text-status-error',
  warning: 'text-status-warning',
  info: 'text-status-info',
} as const satisfies Record<string, string>

/** Localized title/detail per kind — literal keys + the exact interpolation vars each
 * template declares (i18next's typed t can't accept a dynamic key + generic options). */
function useInsightText(insight: InsightOut): { title: string; detail: string } {
  const { t } = useTranslation('dashboard')
  const m = insight.metrics as Record<string, unknown>
  const num = (key: string): number => Number(m[key] ?? 0)
  switch (insight.kind) {
    case 'overdue':
      return {
        title: t('insights.overdue.title', { overdueCount: num('overdueCount') }),
        detail: t('insights.overdue.detail', { overdueCount: num('overdueCount'), overduePercent: num('overduePercent') }),
      }
    case 'high_priority':
      return {
        title: t('insights.highPriority.title', { highPriorityCount: num('highPriorityCount') }),
        detail: t('insights.highPriority.detail', { highPriorityCount: num('highPriorityCount') }),
      }
    case 'risk':
      return {
        title: t('insights.risk.title', { riskCount: num('riskCount') }),
        detail: t('insights.risk.detail', { riskCount: num('riskCount') }),
      }
    case 'workload':
      return {
        title: t('insights.workload.title'),
        detail: t('insights.workload.detail', {
          topAssigneeName: String(m.topAssigneeName ?? ''),
          topLoad: num('topLoad'),
          averageLoad: num('averageLoad'),
        }),
      }
    default:
      return { title: '', detail: '' }
  }
}

export function InsightCard({ insight }: { insight: InsightOut }) {
  const { t } = useTranslation('dashboard')
  const Icon = KIND_ICON[insight.kind as keyof typeof KIND_ICON] ?? Sparkles
  const severityClass = SEVERITY_CLASS[insight.severity as keyof typeof SEVERITY_CLASS] ?? SEVERITY_CLASS.info
  const text = useInsightText(insight)

  return (
    <div className="space-y-2 rounded-md border border-border-default bg-surface-secondary p-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-medium text-text-primary">
          <Icon className={`size-4 ${severityClass}`} />
          {text.title}
        </div>
        <span className={`text-xs font-medium ${severityClass}`}>{t(`severity.${insight.severity}`)}</span>
      </div>
      {insight.detail ? (
        <Markdown content={insight.detail} className="text-xs text-text-secondary" />
      ) : (
        <p className="text-xs text-text-secondary">{text.detail}</p>
      )}
    </div>
  )
}
