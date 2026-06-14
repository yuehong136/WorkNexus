import { type RiskLevel, type SkillInvocationStatus } from '@worknexus/contracts'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { DataTable } from '@/components/patterns/data-table'
import { EmptyState } from '@/components/patterns/empty-state'
import { ErrorState } from '@/components/patterns/error-state'
import { PageSkeleton } from '@/components/patterns/page-skeleton'
import { Button } from '@/components/ui/button'
import { useSkillInvocationsQuery } from '@/features/skills/api/use-skill-invocations-query'
import { useSkillsQuery } from '@/features/skills/api/use-skills-query'
import { skillInvocationColumns } from '@/features/skills/components/skill-invocation-columns'
import { SkillInvocationDrawer } from '@/features/skills/components/skill-invocation-drawer'
import { SkillList } from '@/features/skills/components/skill-list'

const PAGE_SIZE = 20
const RISK_OPTIONS: RiskLevel[] = ['read', 'low_write', 'high_write']
const STATUS_OPTIONS: SkillInvocationStatus[] = ['running', 'success', 'failed', 'blocked', 'rejected']

const selectClassName =
  'h-9 rounded-md border border-border-default bg-surface-primary px-3 text-sm text-text-primary'

export function SkillsPage() {
  const { t } = useTranslation(['common', 'skills'])
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<SkillInvocationStatus | ''>('')
  const [risk, setRisk] = useState<RiskLevel | ''>('')
  const [selected, setSelected] = useState<string | null>(null)

  const skillsQuery = useSkillsQuery()
  const invocationsQuery = useSkillInvocationsQuery({
    page,
    page_size: PAGE_SIZE,
    status: status || undefined,
    risk_level: risk || undefined,
  })

  if (invocationsQuery.isPending) return <PageSkeleton />
  if (invocationsQuery.isError) return <ErrorState onRetry={() => void invocationsQuery.refetch()} />

  const invocations = invocationsQuery.data
  const totalPages = Math.max(1, Math.ceil(invocations.total / invocations.pageSize))

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t('skills:title')}</h1>
        <p className="text-sm text-text-muted">{t('skills:description')}</p>
      </div>

      <section className="space-y-3">
        <div>
          <h2 className="text-base font-semibold text-text-primary">{t('skills:skillsSection.title')}</h2>
          <p className="text-sm text-text-muted">{t('skills:skillsSection.description')}</p>
        </div>
        {skillsQuery.isError ? (
          <ErrorState title={t('skills:skillsSection.error')} onRetry={() => void skillsQuery.refetch()} />
        ) : (
          <SkillList skills={skillsQuery.data ?? []} />
        )}
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-base font-semibold text-text-primary">{t('skills:invocationsSection.title')}</h2>
          <div className="flex gap-2">
            <select
              className={selectClassName}
              value={risk}
              onChange={(e) => {
                setRisk(e.target.value as RiskLevel | '')
                setPage(1)
              }}
            >
              <option value="">{t('skills:filters.allRisks')}</option>
              {RISK_OPTIONS.map((r) => (
                <option key={r} value={r}>
                  {t(`skills:risk.${r}`)}
                </option>
              ))}
            </select>
            <select
              className={selectClassName}
              value={status}
              onChange={(e) => {
                setStatus(e.target.value as SkillInvocationStatus | '')
                setPage(1)
              }}
            >
              <option value="">{t('skills:filters.allStatuses')}</option>
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {t(`skills:status.${s}`)}
                </option>
              ))}
            </select>
          </div>
        </div>

        <DataTable
          columns={skillInvocationColumns(t, setSelected)}
          data={invocations.items}
          emptyState={<EmptyState description={t('skills:invocationsSection.empty')} />}
        />

        {totalPages > 1 ? (
          <div className="flex items-center justify-end gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              {t('pagination.previous')}
            </Button>
            <span className="text-sm text-text-muted">{t('pagination.pageOf', { page, total: totalPages })}</span>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              {t('pagination.next')}
            </Button>
          </div>
        ) : null}
      </section>

      <SkillInvocationDrawer
        invocationId={selected}
        open={selected !== null}
        onOpenChange={(open) => {
          if (!open) setSelected(null)
        }}
      />
    </div>
  )
}
