import { createBrowserRouter } from 'react-router'

import { AppShell } from '@/app/app-shell'
import { GuestOnly } from '@/features/auth/components/guest-only'
import { RequireAuth } from '@/features/auth/components/require-auth'
import { paths } from '@/lib/paths'

export const router = createBrowserRouter([
  {
    element: <GuestOnly />,
    children: [
      {
        path: paths.login(),
        lazy: async () => {
          const { LoginPage } = await import('@/features/auth/routes/login-page')
          return { Component: LoginPage }
        },
      },
      {
        path: paths.setup(),
        lazy: async () => {
          const { SetupPage } = await import('@/features/auth/routes/setup-page')
          return { Component: SetupPage }
        },
      },
    ],
  },
  {
    path: '/invites/:token',
    lazy: async () => {
      const { AcceptInvitePage } = await import('@/features/auth/routes/accept-invite-page')
      return { Component: AcceptInvitePage }
    },
  },
  {
    element: <RequireAuth />,
    children: [
      {
        path: paths.home(),
        element: <AppShell />,
        children: [
          {
            index: true,
            lazy: async () => {
              const { HomePage } = await import('@/features/home/routes/home-page')
              return { Component: HomePage }
            },
          },
          {
            path: paths.projects(),
            lazy: async () => {
              const { ProjectsPage } = await import('@/features/projects/routes/projects-page')
              return { Component: ProjectsPage }
            },
          },
          {
            path: paths.projectDetail(':projectId'),
            lazy: async () => {
              const { ProjectDetailPage } = await import('@/features/projects/routes/project-detail-page')
              return { Component: ProjectDetailPage }
            },
          },
          {
            path: paths.workItems(':projectId'),
            lazy: async () => {
              const { WorkItemsPage } = await import('@/features/work-items/routes/work-items-page')
              return { Component: WorkItemsPage }
            },
          },
          {
            path: paths.board(':projectId'),
            lazy: async () => {
              const { BoardPage } = await import('@/features/work-items/routes/board-page')
              return { Component: BoardPage }
            },
          },
          {
            path: paths.ai(':projectId'),
            lazy: async () => {
              const { AIPage } = await import('@/features/workchat/routes/ai-page')
              return { Component: AIPage }
            },
          },
          {
            path: paths.skills(),
            lazy: async () => {
              const { SkillsPage } = await import('@/features/skills/routes/skills-page')
              return { Component: SkillsPage }
            },
          },
          {
            path: paths.settingsMembers(),
            lazy: async () => {
              const { MembersPage } = await import('@/features/settings/routes/members-page')
              return { Component: MembersPage }
            },
          },
        ],
      },
    ],
  },
])
