import type { WorkItemPriority, WorkItemSource, WorkItemStatus, WorkItemType } from '@worknexus/contracts'
import { useTranslation } from 'react-i18next'

import { Badge } from '@/components/ui/badge'

type BadgeVariant = 'default' | 'secondary' | 'outline' | 'success' | 'warning' | 'error'

const statusVariant: Record<WorkItemStatus, BadgeVariant> = {
  backlog: 'secondary',
  todo: 'outline',
  in_progress: 'default',
  review: 'warning',
  done: 'success',
  cancelled: 'secondary',
}

const priorityVariant: Record<WorkItemPriority, BadgeVariant> = {
  low: 'secondary',
  medium: 'outline',
  high: 'warning',
  urgent: 'error',
}

export function StatusBadge({ status }: { status: WorkItemStatus }) {
  const { t } = useTranslation('workItems')
  return <Badge variant={statusVariant[status]}>{t(`status.${status}`)}</Badge>
}

export function PriorityBadge({ priority }: { priority: WorkItemPriority }) {
  const { t } = useTranslation('workItems')
  return <Badge variant={priorityVariant[priority]}>{t(`priority.${priority}`)}</Badge>
}

export function TypeBadge({ type }: { type: WorkItemType }) {
  const { t } = useTranslation('workItems')
  return <Badge variant="outline">{t(`type.${type}`)}</Badge>
}

export function SourceBadge({ source }: { source: WorkItemSource }) {
  const { t } = useTranslation('workItems')
  const ai = source === 'ai_chat' || source === 'mcp'
  return (
    <Badge variant={ai ? 'default' : 'secondary'}>
      {ai ? `${t('source.aiBadge')} · ` : ''}
      {t(`source.${source}`)}
    </Badge>
  )
}
