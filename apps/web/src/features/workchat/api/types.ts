import type { AgentActionOut } from '@worknexus/contracts'

/** Clean WorkNexus SSE event schema emitted by POST /workchat/runs (see workchat docs §5). */
export type WorkChatEvent =
  | { type: 'message_delta'; content: string }
  | { type: 'agent_action'; action: AgentActionOut }
  | { type: 'knowledge'; references: Array<Record<string, unknown>> }
  | { type: 'error'; message: string; code: number | null }
  | { type: 'message_done'; messageId: string }
  | { type: 'done' }
