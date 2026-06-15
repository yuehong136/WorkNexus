import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'

import { useDashboardOverdueQuery } from '@/features/dashboard/api/use-dashboard-overdue-query'
import { API_BASE, envelope, server } from '@/test/server'

function createWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('useDashboardOverdueQuery', () => {
  it('unwraps the paged overdue payload', async () => {
    const page = {
      items: [
        { id: 'w1', key: 'WNX-1', title: 'late', status: 'todo', type: 'task', priority: 'urgent', daysOverdue: 3 },
      ],
      total: 1,
      page: 1,
      pageSize: 10,
    }
    server.use(http.get(`${API_BASE}/projects/p1/dashboard/overdue`, () => HttpResponse.json(envelope(page))))
    const { result } = renderHook(() => useDashboardOverdueQuery('p1', { page: 1, page_size: 10 }), {
      wrapper: createWrapper(),
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.items[0].daysOverdue).toBe(3)
    expect(result.current.data?.total).toBe(1)
  })
})
