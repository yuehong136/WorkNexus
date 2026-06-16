import type { AuditActorType } from '@worknexus/contracts'
import { useTranslation } from 'react-i18next'

import { Badge } from '@/components/ui/badge'

type BadgeVariant = 'default' | 'secondary' | 'outline'

// Human vs AI vs system at a glance — AI uses the brand fill to stand out as a first-class actor.
const actorVariant: Record<AuditActorType, BadgeVariant> = {
  user: 'secondary',
  ai_agent: 'default',
  system: 'outline',
}

export function ActorBadge({ type, name }: { type: AuditActorType; name: string | null }) {
  const { t } = useTranslation('audit')
  return (
    <span className="flex items-center gap-2">
      <Badge variant={actorVariant[type]}>{t(`actorType.${type}`)}</Badge>
      {name ? <span className="text-sm text-text-primary">{name}</span> : null}
    </span>
  )
}
