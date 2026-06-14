import type { AgentActionStatus } from '@worknexus/contracts'
import { useTranslation } from 'react-i18next'

import { Badge } from '@/components/ui/badge'

type BadgeVariant = 'default' | 'secondary' | 'outline' | 'success' | 'warning' | 'error'

const statusVariant: Record<AgentActionStatus, BadgeVariant> = {
  pending: 'warning',
  approved: 'secondary',
  executed: 'success',
  rejected: 'error',
  failed: 'error',
  expired: 'outline',
}

export function AgentActionStatusBadge({ status }: { status: AgentActionStatus }) {
  const { t } = useTranslation('workchat')
  return <Badge variant={statusVariant[status]}>{t(`status.${status}`)}</Badge>
}
