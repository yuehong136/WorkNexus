import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'

import { useProjectsListQuery } from '@/features/projects/api/use-projects-query'
import { API_BASE, envelope, server } from '@/test/server'

function createWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

const projectPage = {
  items: [
    {
      id: 'p1',
      name: 'WorkNexus Internal',
      key: 'WNX',
      description: null,
      status: 'active',
      ownerId: 'u1',
      owner: { id: 'u1', displayName: 'Owner', email: 'owner@example.com', avatarUrl: null },
      memberCount: 2,
      createdAt: '2026-06-13T00:00:00Z',
      updatedAt: '2026-06-13T00:00:00Z',
    },
  ],
  total: 1,
  page: 1,
  pageSize: 20,
}

describe('useProjectsListQuery', () => {
  it('unwraps the project page payload', async () => {
    server.use(http.get(`${API_BASE}/projects`, () => HttpResponse.json(envelope(projectPage))))
    const { result } = renderHook(() => useProjectsListQuery({ page: 1, pageSize: 20, status: 'active' }), {
      wrapper: createWrapper(),
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.total).toBe(1)
    expect(result.current.data?.items[0].key).toBe('WNX')
    expect(result.current.data?.items[0].memberCount).toBe(2)
  })
})
