import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'

import { useAgentActionsQuery } from '@/features/workchat/api/use-agent-actions-query'
import { API_BASE, envelope, server } from '@/test/server'

function createWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('useAgentActionsQuery', () => {
  it('unwraps the paged agent-action payload', async () => {
    const page = {
      items: [{ id: 'aa1', actionType: 'create_work_item', status: 'pending', conversationId: 'c1' }],
      total: 1,
      page: 1,
      pageSize: 20,
    }
    server.use(http.get(`${API_BASE}/agent-actions`, () => HttpResponse.json(envelope(page))))
    const { result } = renderHook(() => useAgentActionsQuery({ project_id: 'p1', status: 'pending' }), {
      wrapper: createWrapper(),
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.items[0].id).toBe('aa1')
    expect(result.current.data?.items[0].status).toBe('pending')
  })
})
