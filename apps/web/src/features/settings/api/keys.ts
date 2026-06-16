export interface PageQuery {
  page: number
  pageSize: number
}

export const settingsKeys = {
  all: ['settings'] as const,
  users: (params: PageQuery) => [...settingsKeys.all, 'users', params] as const,
  invites: (params: PageQuery) => [...settingsKeys.all, 'invites', params] as const,
  aiConnection: () => [...settingsKeys.all, 'ai-connection'] as const,
  skillCatalog: () => [...settingsKeys.all, 'skill-catalog'] as const,
}
