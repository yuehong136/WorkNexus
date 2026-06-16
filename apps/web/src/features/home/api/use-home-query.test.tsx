import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'

import { useHomeQuery } from '@/features/home/api/use-home-query'
import { API_BASE, envelope, server } from '@/test/server'

function createWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

const emptyCard = { total: 0, items: [] }

describe('useHomeQuery', () => {
  it('unwraps the five-card snapshot', async () => {
    const snapshot = {
      myTodos: { total: 2, items: [{ id: 'w1', key: 'P-1', projectId: 'p1', title: 'Todo' }] },
      overdue: emptyCard,
      pendingAgentActions: {
        total: 1,
        items: [{ id: 'a1', projectId: 'p1', actionType: 'create_work_item', riskLevel: 'low_write' }],
      },
      recentAiCreated: emptyCard,
      pendingIntake: emptyCard,
    }
    server.use(http.get(`${API_BASE}/home`, () => HttpResponse.json(envelope(snapshot))))

    const { result } = renderHook(() => useHomeQuery(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.myTodos.total).toBe(2)
    expect(result.current.data?.pendingAgentActions.items[0].actionType).toBe('create_work_item')
  })
})
