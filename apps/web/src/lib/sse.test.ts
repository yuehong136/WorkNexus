import { afterEach, describe, expect, it, vi } from 'vitest'

import { APIError } from '@/lib/api-client'
import { streamSSE } from '@/lib/sse'

function sseResponse(frames: string[]): Response {
  const body = frames.map((frame) => `data: ${frame}\n\n`).join('')
  return new Response(body, { status: 200, headers: { 'content-type': 'text/event-stream' } })
}

afterEach(() => vi.restoreAllMocks())

describe('streamSSE', () => {
  it('parses data frames into JSON events in order', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      sseResponse(['{"type":"message_delta","content":"hi"}', '{"type":"done"}']),
    )
    const events: unknown[] = []
    await streamSSE('/workchat/runs', { conversationId: 'c1', content: 'x' }, { onEvent: (e) => events.push(e) })
    expect(events).toEqual([{ type: 'message_delta', content: 'hi' }, { type: 'done' }])
  })

  it('skips malformed frames without aborting the stream', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(sseResponse(['not json at all', '{"type":"done"}']))
    const events: unknown[] = []
    await streamSSE('/x', {}, { onEvent: (e) => events.push(e) })
    expect(events).toEqual([{ type: 'done' }])
  })

  it('throws an APIError when the response is not ok', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('nope', { status: 500 }))
    await expect(streamSSE('/x', {}, { onEvent: () => {} })).rejects.toBeInstanceOf(APIError)
  })
})
