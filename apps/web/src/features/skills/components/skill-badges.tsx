import type { RiskLevel, SkillInvocationStatus } from '@worknexus/contracts'
import { useTranslation } from 'react-i18next'

import { Badge } from '@/components/ui/badge'

type BadgeVariant = 'default' | 'secondary' | 'outline' | 'success' | 'warning' | 'error'

const riskVariant: Record<RiskLevel, BadgeVariant> = {
  read: 'secondary',
  low_write: 'warning',
  high_write: 'error',
}

const statusVariant: Record<SkillInvocationStatus, BadgeVariant> = {
  running: 'secondary',
  success: 'success',
  failed: 'error',
  blocked: 'warning',
  rejected: 'error',
}

export function RiskBadge({ risk }: { risk: RiskLevel | null }) {
  const { t } = useTranslation('skills')
  if (!risk) return <span className="text-text-muted">{t('common.none')}</span>
  return <Badge variant={riskVariant[risk]}>{t(`risk.${risk}`)}</Badge>
}

export function InvocationStatusBadge({ status }: { status: SkillInvocationStatus }) {
  const { t } = useTranslation('skills')
  return <Badge variant={statusVariant[status]}>{t(`status.${status}`)}</Badge>
}
