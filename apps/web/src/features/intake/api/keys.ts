import type { ListIntakeParams } from '@worknexus/contracts'

export const intakeKeys = {
  all: ['intake'] as const,
  lists: (projectId: string) => [...intakeKeys.all, 'list', projectId] as const,
  list: (projectId: string, params: ListIntakeParams) => [...intakeKeys.lists(projectId), params] as const,
  detail: (id: string) => [...intakeKeys.all, 'detail', id] as const,
}
