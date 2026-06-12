import { Inbox, type LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

interface EmptyStateProps {
  icon?: LucideIcon
  title?: string
  description?: string
  action?: ReactNode
}

export function EmptyState({ icon: Icon = Inbox, title, description, action }: EmptyStateProps) {
  const { t } = useTranslation()
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border-default p-10 text-center">
      <Icon className="size-8 text-text-muted" />
      <p className="text-sm font-medium text-text-primary">{title ?? t('empty.title')}</p>
      {description ? <p className="text-sm text-text-muted">{description}</p> : null}
      {action}
    </div>
  )
}
