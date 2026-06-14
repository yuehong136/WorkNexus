import { API_BASE_URL, APIError } from '@/lib/api-client'

/**
 * Stream a Server-Sent-Events POST endpoint (AGENTS §5.1: the one sanctioned place to
 * bypass the contracts client). Uses fetch + ReadableStream rather than EventSource so we
 * can POST and send the session cookie (credentials: 'include').
 *
 * Each `data:` line carries one JSON event; malformed frames are skipped, not thrown.
 */
export interface StreamHandlers {
  signal?: AbortSignal
  onEvent: (event: unknown) => void
}

export async function streamSSE(path: string, body: unknown, { signal, onEvent }: StreamHandlers): Promise<void> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify(body),
    signal,
  })
  if (!response.ok || !response.body) {
    throw new APIError(-1, `stream failed (${response.status})`, response.status)
  }

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += value
    // SSE frames are separated by a blank line; keep the trailing partial in the buffer.
    const frames = buffer.split('\n\n')
    buffer = frames.pop() ?? ''
    for (const frame of frames) {
      dispatchFrame(frame, onEvent)
    }
  }
  if (buffer.trim()) dispatchFrame(buffer, onEvent)
}

function dispatchFrame(frame: string, onEvent: (event: unknown) => void): void {
  const dataLine = frame.split('\n').find((line) => line.startsWith('data:'))
  if (!dataLine) return
  const payload = dataLine.slice('data:'.length).trim()
  if (!payload) return
  try {
    onEvent(JSON.parse(payload))
  } catch {
    // Skip malformed frames — one bad event must not abort the stream.
  }
}
