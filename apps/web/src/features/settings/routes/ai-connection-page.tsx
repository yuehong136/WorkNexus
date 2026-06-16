import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import { ErrorState } from '@/components/patterns/error-state'
import { PageSkeleton } from '@/components/patterns/page-skeleton'
import { Badge } from '@/components/ui/badge'
import { useAiConnectionQuery } from '@/features/settings/api/use-ai-connection-query'

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <dt className="text-sm text-text-muted">{label}</dt>
      <dd className="text-sm text-text-primary">{children}</dd>
    </div>
  )
}

export function AiConnectionPage() {
  const { t } = useTranslation('settings')
  const query = useAiConnectionQuery()

  if (query.isPending) return <PageSkeleton />
  if (query.isError) return <ErrorState onRetry={() => void query.refetch()} />

  const c = query.data
  return (
    <div className="max-w-lg space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-text-primary">{t('ai.title')}</h2>
        <p className="text-sm text-text-muted">{t('ai.description')}</p>
      </div>

      <dl className="space-y-3 rounded-lg border border-border-default bg-surface-primary p-4">
        <Row label={t('ai.client')}>
          <span className="font-mono text-xs">{c.aiClient}</span>
        </Row>
        <Row label={t('ai.baseUrl')}>
          <span className="font-mono text-xs">{c.aiPlatformBaseUrl}</span>
        </Row>
        <Row label={t('ai.defaultAgentId')}>
          <span className="font-mono text-xs">{c.aiPlatformDefaultAgentId || '—'}</span>
        </Row>
        <Row label={t('ai.timeout')}>{c.aiPlatformTimeoutSeconds}</Row>
        <Row label={t('ai.apiKey')}>
          {c.apiKeyConfigured ? (
            <span className="flex items-center gap-2">
              <Badge variant="success">{t('ai.configured')}</Badge>
              <span className="font-mono text-xs">{c.apiKeyMasked}</span>
            </span>
          ) : (
            <Badge variant="outline">{t('ai.notConfigured')}</Badge>
          )}
        </Row>
        <Row label={t('ai.triageProvider')}>{c.intakeTriageProvider}</Row>
        <Row label={t('ai.insightsProvider')}>{c.dashboardInsightsProvider}</Row>
      </dl>

      <p className="text-xs text-text-muted">{t('ai.note')}</p>
    </div>
  )
}
