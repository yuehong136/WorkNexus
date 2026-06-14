import { Bot } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router'

import { EmptyState } from '@/components/patterns/empty-state'
import { ErrorState } from '@/components/patterns/error-state'
import { PageSkeleton } from '@/components/patterns/page-skeleton'
import { useConversationsQuery } from '@/features/workchat/api/use-conversations-query'
import { AIChatPanel } from '@/features/workchat/components/ai-chat-panel'
import { useHasPermission } from '@/lib/auth/use-has-permission'

export function AIPage() {
  const { t } = useTranslation('workchat')
  const { projectId = '' } = useParams()
  const canUse = useHasPermission('workchat.use', projectId)
  const conversationsQuery = useConversationsQuery(projectId)

  if (!canUse) return <EmptyState title={t('noAccess')} />
  if (conversationsQuery.isPending) return <PageSkeleton />
  if (conversationsQuery.isError) return <ErrorState onRetry={() => void conversationsQuery.refetch()} />

  const conversation = conversationsQuery.data[0]
  if (!conversation) return <EmptyState title={t('empty.title')} />

  return (
    <div className="flex h-full flex-col gap-4">
      <div className="flex items-center gap-2">
        <Bot className="size-5 text-brand-primary" />
        <h1 className="text-xl font-semibold text-text-primary">{t('title')}</h1>
      </div>
      <div className="min-h-0 flex-1">
        <AIChatPanel conversationId={conversation.id} projectId={projectId} />
      </div>
    </div>
  )
}
