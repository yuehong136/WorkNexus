import type { ListWorkItemsParams } from '@worknexus/contracts'

export const workItemKeys = {
  all: ['workItems'] as const,
  lists: (projectId: string) => [...workItemKeys.all, 'list', projectId] as const,
  list: (projectId: string, params: ListWorkItemsParams) =>
    [...workItemKeys.lists(projectId), params] as const,
  detail: (id: string) => [...workItemKeys.all, 'detail', id] as const,
  comments: (id: string) => [...workItemKeys.all, 'comments', id] as const,
  activities: (id: string) => [...workItemKeys.all, 'activities', id] as const,
  relations: (id: string) => [...workItemKeys.all, 'relations', id] as const,
}
