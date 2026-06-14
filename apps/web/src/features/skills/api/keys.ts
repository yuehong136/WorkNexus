import type { ListSkillInvocationsParams } from '@worknexus/contracts'

export const skillKeys = {
  all: ['skills'] as const,
  catalog: () => [...skillKeys.all, 'catalog'] as const,
  invocationsList: () => [...skillKeys.all, 'invocations'] as const,
  invocations: (params: ListSkillInvocationsParams) => [...skillKeys.invocationsList(), params] as const,
  invocationDetail: (id: string) => [...skillKeys.all, 'invocation', id] as const,
}
