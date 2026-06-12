import type { CurrentUserContext } from '@worknexus/contracts'

export function makeCurrentUserContext(overrides?: Partial<CurrentUserContext>): CurrentUserContext {
  return {
    user: {
      id: 'user-1',
      email: 'owner@example.com',
      displayName: 'Owner',
      avatarUrl: null,
      identityProvider: 'local',
      externalUserId: null,
    },
    tenant: { id: 'tenant-1', name: 'Test Workspace', slug: 'default' },
    roles: ['owner'],
    permissions: ['user.read', 'user.invite', 'project.read'],
    projects: [
      { id: 'project-1', name: 'WorkNexus Internal', role: 'owner', permissions: ['project.read', 'work_item.read'] },
    ],
    ai: { availableAgents: [{ id: 'agent-1', name: 'WorkNexus Assistant', status: 'active' }] },
    ...overrides,
  }
}
