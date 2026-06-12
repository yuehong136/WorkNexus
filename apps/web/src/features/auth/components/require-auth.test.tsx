import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { describe, expect, it } from 'vitest'

import { RequireAuth } from '@/features/auth/components/require-auth'
import { paths } from '@/lib/paths'
import { makeCurrentUserContext } from '@/test/factories'
import { API_BASE, envelope, server } from '@/test/server'

function renderGuarded() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createMemoryRouter(
    [
      { path: paths.login(), element: <div>login-page</div> },
      { path: paths.setup(), element: <div>setup-page</div> },
      {
        element: <RequireAuth />,
        children: [{ path: paths.home(), element: <div>protected-content</div> }],
      },
    ],
    { initialEntries: [paths.home()] },
  )
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('RequireAuth', () => {
  it('redirects to /setup when the instance is not initialized', async () => {
    server.use(
      http.get(`${API_BASE}/setup/status`, () => HttpResponse.json(envelope({ initialized: false }))),
    )
    renderGuarded()
    expect(await screen.findByText('setup-page')).toBeInTheDocument()
  })

  it('redirects to /login when unauthenticated', async () => {
    server.use(
      http.get(`${API_BASE}/setup/status`, () => HttpResponse.json(envelope({ initialized: true }))),
      http.get(`${API_BASE}/me`, () =>
        HttpResponse.json({ code: 1003, message: 'not authenticated' }, { status: 401 }),
      ),
    )
    renderGuarded()
    expect(await screen.findByText('login-page')).toBeInTheDocument()
  })

  it('renders the protected outlet when authenticated', async () => {
    server.use(
      http.get(`${API_BASE}/setup/status`, () => HttpResponse.json(envelope({ initialized: true }))),
      http.get(`${API_BASE}/me`, () => HttpResponse.json(envelope(makeCurrentUserContext()))),
    )
    renderGuarded()
    expect(await screen.findByText('protected-content')).toBeInTheDocument()
  })
})
