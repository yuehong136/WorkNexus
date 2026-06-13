export const paths = {
  home: () => '/',
  login: () => '/login',
  setup: () => '/setup',
  invite: (token: string) => `/invites/${token}`,
  projects: () => '/projects',
  projectDetail: (id: string) => `/projects/${id}`,
  settingsMembers: () => '/settings/members',
} as const
