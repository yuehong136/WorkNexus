export interface PageQuery {
  page: number
  pageSize: number
}

export const settingsKeys = {
  all: ['settings'] as const,
  users: (params: PageQuery) => [...settingsKeys.all, 'users', params] as const,
  invites: (params: PageQuery) => [...settingsKeys.all, 'invites', params] as const,
}
