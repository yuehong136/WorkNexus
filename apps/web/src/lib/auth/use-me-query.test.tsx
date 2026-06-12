import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'

import { APIError } from '@/lib/api-client'
import { useMeQuery } from '@/lib/auth/use-me-query'
import { makeCurrentUserContext } from '@/test/factories'
import { API_BASE, envelope, server } from '@/test/server'

function createWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('useMeQuery', () => {
  it('returns the unwrapped CurrentUserContext on success', async () => {
    server.use(http.get(`${API_BASE}/me`, () => HttpResponse.json(envelope(makeCurrentUserContext()))))
    const { result } = renderHook(() => useMeQuery(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.user.email).toBe('owner@example.com')
    expect(result.current.data?.roles).toEqual(['owner'])
  })

  it('errors with an APIError carrying status 401 when unauthenticated', async () => {
    server.use(
      http.get(`${API_BASE}/me`, () =>
        HttpResponse.json({ code: 1003, message: 'not authenticated' }, { status: 401 }),
      ),
    )
    const { result } = renderHook(() => useMeQuery(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isError).toBe(true))
    const error = result.current.error
    expect(error).toBeInstanceOf(APIError)
    expect((error as APIError).status).toBe(401)
    expect((error as APIError).code).toBe(1003)
  })
})
