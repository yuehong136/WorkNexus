export const paths = {
  home: () => '/',
  login: () => '/login',
  setup: () => '/setup',
  invite: (token: string) => `/invites/${token}`,
  projects: () => '/projects',
  projectDetail: (id: string) => `/projects/${id}`,
  workItems: (projectId: string) => `/projects/${projectId}/work-items`,
  board: (projectId: string) => `/projects/${projectId}/board`,
  skills: () => '/skills',
  settingsMembers: () => '/settings/members',
} as const
