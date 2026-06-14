import type { ListAgentActionsParams } from '@worknexus/contracts'

export const workchatKeys = {
  all: ['workchat'] as const,
  conversations: (projectId: string) => [...workchatKeys.all, 'conversations', projectId] as const,
  messages: (conversationId: string) => [...workchatKeys.all, 'messages', conversationId] as const,
  agentActions: () => [...workchatKeys.all, 'agentActions'] as const,
  agentActionList: (params: ListAgentActionsParams) => [...workchatKeys.agentActions(), params] as const,
}
