import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'

import { useSkillInvocationsQuery } from '@/features/skills/api/use-skill-invocations-query'
import { useSkillsQuery } from '@/features/skills/api/use-skills-query'
import { API_BASE, envelope, server } from '@/test/server'

function createWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('useSkillsQuery', () => {
  it('unwraps the reflected skill catalog', async () => {
    const skills = [
      {
        skillCode: 'workitem-skill',
        tools: [
          { toolName: 'workitem_get_work_item', riskLevel: 'read', executableInV01: true, requiredPermission: 'work_item.read' },
          { toolName: 'workitem_create_work_item', riskLevel: 'low_write', executableInV01: false, requiredPermission: 'work_item.create' },
        ],
      },
    ]
    server.use(http.get(`${API_BASE}/skills`, () => HttpResponse.json(envelope(skills))))
    const { result } = renderHook(() => useSkillsQuery(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.[0].skillCode).toBe('workitem-skill')
    expect(result.current.data?.[0].tools[0].executableInV01).toBe(true)
  })
})

describe('useSkillInvocationsQuery', () => {
  it('unwraps the invocation page payload', async () => {
    const pageData = {
      items: [
        {
          id: 'inv1',
          skillCode: 'workitem-skill',
          toolName: 'workitem_get_work_item',
          callerType: 'ai_agent',
          callerId: 'a1',
          representedUserId: 'u1',
          representedUser: { id: 'u1', displayName: 'Owner' },
          agentId: 'a1',
          projectId: 'p1',
          conversationId: null,
          runId: null,
          inputSummary: '{}',
          outputSummary: '{}',
          status: 'success',
          riskLevel: 'read',
          requiresConfirmation: false,
          agentActionId: null,
          auditLogId: 'log1',
          errorMessage: null,
          startedAt: '2026-06-14T00:00:00Z',
          finishedAt: '2026-06-14T00:00:01Z',
          createdAt: '2026-06-14T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      pageSize: 20,
    }
    server.use(http.get(`${API_BASE}/skills/invocations`, () => HttpResponse.json(envelope(pageData))))
    const { result } = renderHook(() => useSkillInvocationsQuery({ page: 1, page_size: 20 }), {
      wrapper: createWrapper(),
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.total).toBe(1)
    expect(result.current.data?.items[0].representedUser?.displayName).toBe('Owner')
  })
})
