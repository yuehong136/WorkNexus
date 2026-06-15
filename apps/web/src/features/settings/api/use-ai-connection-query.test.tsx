import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'

import { useAiConnectionQuery } from '@/features/settings/api/use-ai-connection-query'
import { API_BASE, envelope, server } from '@/test/server'

function createWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('useAiConnectionQuery', () => {
  it('unwraps the masked connection (token never plaintext)', async () => {
    const data = {
      aiClient: 'multirag',
      aiPlatformBaseUrl: 'http://platform.test:8123',
      aiPlatformDefaultAgentId: 'agent-1',
      aiPlatformTimeoutSeconds: 60,
      apiKeyConfigured: true,
      apiKeyMasked: '••••9999',
      intakeTriageProvider: 'rules',
      dashboardInsightsProvider: 'rules',
    }
    server.use(http.get(`${API_BASE}/settings/ai-connection`, () => HttpResponse.json(envelope(data))))

    const { result } = renderHook(() => useAiConnectionQuery(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.apiKeyConfigured).toBe(true)
    expect(result.current.data?.apiKeyMasked).toBe('••••9999')
    expect(result.current.data?.aiClient).toBe('multirag')
  })
})
