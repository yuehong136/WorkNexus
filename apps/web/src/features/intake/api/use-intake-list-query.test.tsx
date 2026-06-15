import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'

import { useIntakeListQuery } from '@/features/intake/api/use-intake-list-query'
import { API_BASE, envelope, server } from '@/test/server'

function createWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('useIntakeListQuery', () => {
  it('unwraps the paged intake payload', async () => {
    const page = {
      items: [{ id: 'i1', title: 'Login crash', status: 'new', source: 'manual', suggestedType: 'bug' }],
      total: 1,
      page: 1,
      pageSize: 20,
    }
    server.use(http.get(`${API_BASE}/projects/p1/intake`, () => HttpResponse.json(envelope(page))))
    const { result } = renderHook(() => useIntakeListQuery('p1', { page: 1, page_size: 20 }), {
      wrapper: createWrapper(),
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.items[0].id).toBe('i1')
    expect(result.current.data?.items[0].status).toBe('new')
  })
})
