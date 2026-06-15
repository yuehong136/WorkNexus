import type { IntakeOut } from '@worknexus/contracts'
import { Sparkles } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'

export function TriageSuggestionCard({
  intake,
  canTriage,
  onAdopt,
}: {
  intake: IntakeOut
  canTriage: boolean
  onAdopt: () => void
}) {
  const { t } = useTranslation(['common', 'intake', 'workItems'])
  const meta = intake.triageMeta ?? null
  const provider = typeof meta?.provider === 'string' ? meta.provider : null
  const version = typeof meta?.version === 'string' ? meta.version : '1'

  return (
    <div className="space-y-3 rounded-md border border-border-default bg-surface-secondary p-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-medium text-text-primary">
          <Sparkles className="size-4 text-text-muted" />
          {t('intake:suggestion.title')}
        </div>
        {provider ? (
          <span className="text-xs text-text-muted">{t('intake:suggestion.provider', { provider, version })}</span>
        ) : null}
      </div>
      <p className="text-xs text-text-muted">{t('intake:suggestion.advisoryNote')}</p>
      <dl className="grid grid-cols-2 gap-3 text-sm">
        <div className="col-span-2 space-y-1">
          <dt className="text-xs text-text-muted">{t('intake:suggestion.summary')}</dt>
          <dd className="text-text-primary">{intake.aiSummary ?? t('intake:suggestion.none')}</dd>
        </div>
        <div className="space-y-1">
          <dt className="text-xs text-text-muted">{t('intake:suggestion.suggestedType')}</dt>
          <dd className="text-text-primary">
            {intake.suggestedType ? t(`workItems:type.${intake.suggestedType}`) : t('intake:suggestion.none')}
          </dd>
        </div>
        <div className="space-y-1">
          <dt className="text-xs text-text-muted">{t('intake:suggestion.suggestedPriority')}</dt>
          <dd className="text-text-primary">
            {intake.suggestedPriority
              ? t(`workItems:priority.${intake.suggestedPriority}`)
              : t('intake:suggestion.none')}
          </dd>
        </div>
      </dl>
      {canTriage ? (
        <Button size="sm" variant="outline" onClick={onAdopt}>
          {t('intake:suggestion.adopt')}
        </Button>
      ) : null}
    </div>
  )
}
