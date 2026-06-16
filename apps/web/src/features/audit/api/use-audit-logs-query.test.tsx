import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'

import { useAuditLogsQuery } from '@/features/audit/api/use-audit-logs-query'
import { API_BASE, envelope, server } from '@/test/server'

function createWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('useAuditLogsQuery', () => {
  it('unwraps the audit page and resolves actor display names', async () => {
    const pageData = {
      items: [
        {
          id: 'log1',
          createdAt: '2026-06-14T00:00:00Z',
          actor: { type: 'ai_agent', id: 'a1', displayName: 'Helper Agent' },
          action: 'ai.proposed_action.create',
          resourceType: 'agent_action',
          resourceId: 'aa1',
          projectId: 'p1',
          projectName: 'Alpha',
          before: null,
          after: null,
          detail: { skillInvocationId: 'si1' },
          requestId: 'req1',
          ipAddress: null,
        },
      ],
      total: 1,
      page: 1,
      pageSize: 20,
    }
    server.use(http.get(`${API_BASE}/audit-logs`, () => HttpResponse.json(envelope(pageData))))

    const { result } = renderHook(() => useAuditLogsQuery({ page: 1, page_size: 20 }), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.total).toBe(1)
    expect(result.current.data?.items[0].actor.displayName).toBe('Helper Agent')
    expect(result.current.data?.items[0].actor.type).toBe('ai_agent')
  })
})
