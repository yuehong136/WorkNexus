import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'

import { useAcceptIntakeMutation } from '@/features/intake/api/use-accept-intake-mutation'
import { API_BASE, envelope, server } from '@/test/server'

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('useAcceptIntakeMutation', () => {
  it('posts accept and returns the converted intake', async () => {
    server.use(
      http.post(`${API_BASE}/intake/i1/accept`, () =>
        HttpResponse.json(envelope({ id: 'i1', status: 'converted', convertedWorkItemId: 'w1' })),
      ),
    )
    const { result } = renderHook(() => useAcceptIntakeMutation('p1'), { wrapper: createWrapper() })
    result.current.mutate({ intakeId: 'i1', body: { type: 'bug' } })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.status).toBe('converted')
    expect(result.current.data?.convertedWorkItemId).toBe('w1')
  })
})
