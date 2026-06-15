import type { IntakeSource, IntakeStatus } from '@worknexus/contracts'
import { useTranslation } from 'react-i18next'

import { Badge } from '@/components/ui/badge'

type BadgeVariant = 'default' | 'secondary' | 'outline' | 'success' | 'warning' | 'error'

const statusVariant: Record<IntakeStatus, BadgeVariant> = {
  new: 'default',
  triaging: 'warning',
  accepted: 'outline',
  rejected: 'secondary',
  duplicate: 'secondary',
  snoozed: 'outline',
  converted: 'success',
}

export function IntakeStatusBadge({ status }: { status: IntakeStatus }) {
  const { t } = useTranslation('intake')
  return <Badge variant={statusVariant[status]}>{t(`status.${status}`)}</Badge>
}

export function IntakeSourceBadge({ source }: { source: IntakeSource }) {
  const { t } = useTranslation('intake')
  const ai = source === 'ai_chat' || source === 'mcp'
  return (
    <Badge variant={ai ? 'default' : 'secondary'}>
      {ai ? `${t('source.aiBadge')} · ` : ''}
      {t(`source.${source}`)}
    </Badge>
  )
}
