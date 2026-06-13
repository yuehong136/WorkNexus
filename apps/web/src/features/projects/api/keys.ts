import type { ProjectStatus } from '@worknexus/contracts'

export interface ProjectsListQuery {
  page: number
  pageSize: number
  status: ProjectStatus
}

export const projectKeys = {
  all: ['projects'] as const,
  list: (params: ProjectsListQuery) => [...projectKeys.all, 'list', params] as const,
  detail: (id: string) => [...projectKeys.all, 'detail', id] as const,
  members: (id: string) => [...projectKeys.all, 'members', id] as const,
}
