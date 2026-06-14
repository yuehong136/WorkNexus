import { useQueryClient } from '@tanstack/react-query'
import type { AgentActionOut } from '@worknexus/contracts'
import { useCallback, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import type { WorkChatEvent } from '@/features/workchat/api/types'
import { workchatKeys } from '@/features/workchat/api/keys'
import { APIError } from '@/lib/api-client'
import { streamSSE } from '@/lib/sse'

interface RunState {
  streaming: boolean
  pendingUser: string | null
  draft: string
  liveActions: AgentActionOut[]
  error: string | null
}

const IDLE: RunState = { streaming: false, pendingUser: null, draft: '', liveActions: [], error: null }

/** Drives one AI turn over SSE and accumulates the live transcript. On completion it
 * invalidates the persisted messages + agent-actions queries so the panel reconciles. */
export function useWorkchatRun(conversationId: string) {
  const { t } = useTranslation('workchat')
  const queryClient = useQueryClient()
  const [state, setState] = useState<RunState>(IDLE)
  const abortRef = useRef<AbortController | null>(null)

  const send = useCallback(
    async (content: string) => {
      if (!content.trim() || state.streaming) return
      const controller = new AbortController()
      abortRef.current = controller
      setState({ streaming: true, pendingUser: content, draft: '', liveActions: [], error: null })
      try {
        await streamSSE(
          '/workchat/runs',
          { conversationId, content },
          {
            signal: controller.signal,
            onEvent: (raw) => {
              const event = raw as WorkChatEvent
              if (event.type === 'message_delta') {
                setState((s) => ({ ...s, draft: s.draft + event.content }))
              } else if (event.type === 'agent_action') {
                setState((s) => ({ ...s, liveActions: [...s.liveActions, event.action] }))
              } else if (event.type === 'error') {
                setState((s) => ({ ...s, error: event.message }))
              }
            },
          },
        )
      } catch (error) {
        const message = error instanceof APIError ? error.message : t('run.failed')
        setState((s) => ({ ...s, error: message }))
      } finally {
        abortRef.current = null
        setState((s) => ({ ...s, streaming: false, pendingUser: null, draft: '' }))
        await queryClient.invalidateQueries({ queryKey: workchatKeys.messages(conversationId) })
        await queryClient.invalidateQueries({ queryKey: workchatKeys.agentActions() })
      }
    },
    [conversationId, queryClient, state.streaming, t],
  )

  const cancel = useCallback(() => abortRef.current?.abort(), [])

  return { ...state, send, cancel }
}
