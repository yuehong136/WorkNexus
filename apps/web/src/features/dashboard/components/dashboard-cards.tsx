import type { DashboardSummaryOut } from '@worknexus/contracts'
import { useTranslation } from 'react-i18next'

function StatCard({ label, value, hint }: { label: string; value: number | string; hint?: string }) {
  return (
    <div className="rounded-lg border border-border-default bg-surface-primary p-4">
      <div className="text-2xl font-semibold text-text-primary">{value}</div>
      <div className="text-xs text-text-muted">{label}</div>
      {hint ? <div className="mt-0.5 text-xs text-text-muted">{hint}</div> : null}
    </div>
  )
}

export function DashboardCards({ summary }: { summary: DashboardSummaryOut }) {
  const { t } = useTranslation('dashboard')
  const conversion = `${Math.round(summary.intakeConversionRate * 100)}%`
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-6">
      <StatCard label={t('cards.total')} value={summary.totalCount} />
      <StatCard label={t('cards.highPriority')} value={summary.highPriorityCount} />
      <StatCard label={t('cards.overdue')} value={summary.overdueCount} />
      <StatCard label={t('cards.aiCreated')} value={summary.aiCreatedCount} />
      <StatCard label={t('cards.intakeRequests')} value={summary.intakeRequestCount} />
      <StatCard
        label={t('cards.intakeConverted')}
        value={summary.intakeConvertedCount}
        hint={t('cards.conversionRate', { rate: conversion })}
      />
    </div>
  )
}
