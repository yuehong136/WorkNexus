import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'

import { useDashboardSummaryQuery } from '@/features/dashboard/api/use-dashboard-summary-query'
import { API_BASE, envelope, server } from '@/test/server'

function createWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('useDashboardSummaryQuery', () => {
  it('unwraps the summary payload', async () => {
    const summary = {
      totalCount: 5,
      statusCounts: { backlog: 5 },
      typeCounts: { task: 5 },
      priorityCounts: { medium: 5 },
      sourceCounts: { manual: 4, ai_chat: 1 },
      highPriorityCount: 0,
      overdueCount: 1,
      aiCreatedCount: 1,
      intakeRequestCount: 2,
      intakeStatusCounts: { new: 2 },
      intakeConvertedCount: 0,
      intakeConversionRate: 0,
      createdTrend: [{ date: '2026-06-15', count: 5 }],
      completedTrend: [{ date: '2026-06-15', count: 0 }],
    }
    server.use(http.get(`${API_BASE}/projects/p1/dashboard/summary`, () => HttpResponse.json(envelope(summary))))
    const { result } = renderHook(() => useDashboardSummaryQuery('p1'), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.totalCount).toBe(5)
    expect(result.current.data?.aiCreatedCount).toBe(1)
    expect(result.current.data?.createdTrend).toHaveLength(1)
  })
})
