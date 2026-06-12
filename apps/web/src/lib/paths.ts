export const paths = {
  home: () => '/',
  login: () => '/login',
  setup: () => '/setup',
  invite: (token: string) => `/invites/${token}`,
  settingsMembers: () => '/settings/members',
} as const
