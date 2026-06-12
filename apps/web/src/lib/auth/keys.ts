export const authKeys = {
  all: ['auth'] as const,
  me: () => [...authKeys.all, 'me'] as const,
  setupStatus: () => [...authKeys.all, 'setup-status'] as const,
  invitePreview: (token: string) => [...authKeys.all, 'invite-preview', token] as const,
}
