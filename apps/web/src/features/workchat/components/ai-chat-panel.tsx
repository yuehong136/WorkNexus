import type { AgentActionOut } from '@worknexus/contracts'
import { SendHorizontal } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { EmptyState } from '@/components/patterns/empty-state'
import { ErrorState } from '@/components/patterns/error-state'
import { PageSkeleton } from '@/components/patterns/page-skeleton'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { useAgentActionsQuery } from '@/features/workchat/api/use-agent-actions-query'
import { useMessagesQuery } from '@/features/workchat/api/use-messages-query'
import { useWorkchatRun } from '@/features/workchat/api/use-workchat-run'
import { AgentActionCard } from '@/features/workchat/components/agent-action-card'
import { MessageBubble } from '@/features/workchat/components/message-bubble'

export function AIChatPanel({ conversationId, projectId }: { conversationId: string; projectId: string }) {
  const { t } = useTranslation('workchat')
  const messagesQuery = useMessagesQuery(conversationId)
  const actionsQuery = useAgentActionsQuery({ project_id: projectId, status: 'pending' })
  const run = useWorkchatRun(conversationId)
  const [input, setInput] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)

  const messages = messagesQuery.data?.items ?? []

  const pendingActions = useMemo<AgentActionOut[]>(() => {
    const byId = new Map((actionsQuery.data?.items ?? []).map((action) => [action.id, action]))
    if (run.streaming) {
      for (const action of run.liveActions) if (!byId.has(action.id)) byId.set(action.id, action)
    }
    return [...byId.values()].filter((action) => action.conversationId === conversationId)
  }, [actionsQuery.data, run.streaming, run.liveActions, conversationId])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight })
  }, [messages.length, run.draft, run.pendingUser, pendingActions.length])

  const submit = () => {
    const content = input.trim()
    if (!content || run.streaming) return
    setInput('')
    void run.send(content)
  }

  if (messagesQuery.isPending) return <PageSkeleton />
  if (messagesQuery.isError) return <ErrorState onRetry={() => void messagesQuery.refetch()} />

  const isEmpty = messages.length === 0 && !run.pendingUser

  return (
    <div className="flex h-full flex-col gap-3">
      <div ref={scrollRef} className="flex-1 space-y-3 overflow-auto">
        {isEmpty ? (
          <EmptyState title={t('empty.title')} description={t('empty.description')} />
        ) : (
          messages.map((message) => (
            <MessageBubble key={message.id} role={message.role} content={message.content} />
          ))
        )}
        {run.pendingUser ? <MessageBubble role="user" content={run.pendingUser} /> : null}
        {run.streaming || run.draft ? <MessageBubble role="ai" content={run.draft} pending /> : null}
        {pendingActions.map((action) => (
          <AgentActionCard key={action.id} action={action} />
        ))}
        {run.error ? <ErrorState message={run.error} /> : null}
      </div>

      <div className="flex items-end gap-2 border-t border-border-default pt-3">
        <Textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              submit()
            }
          }}
          placeholder={t('input.placeholder')}
          rows={2}
          className="resize-none"
          disabled={run.streaming}
        />
        <Button onClick={submit} disabled={run.streaming || !input.trim()} aria-label={t('input.send')}>
          <SendHorizontal className="size-4" />
        </Button>
      </div>
    </div>
  )
}
