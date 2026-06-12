import { createBrowserRouter } from 'react-router'

import { AppShell } from '@/app/app-shell'
import { paths } from '@/lib/paths'

export const router = createBrowserRouter([
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
    ],
  },
])
