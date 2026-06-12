export class APIError extends Error {
  readonly code: number
  readonly status: number

  constructor(code: number, message: string, status: number) {
    super(message)
    this.name = 'APIError'
    this.code = code
    this.status = status
  }
}

interface EnvelopeBody {
  code: number
  message: string
  data?: unknown
}

const BASE_URL =
  (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) || 'http://localhost:8200/api/v1'

/**
 * Session auth rides on an HttpOnly cookie, so every request must send
 * credentials. The envelope is checked here (code !== 0 -> APIError) but NOT
 * unwrapped: orval's generated fetch client types the response as
 * { data: Envelope<T>, status, headers }, so we return exactly that shape.
 * Use `unwrap()` from apps/web `lib/api-client.ts` at call sites.
 */
export async function apiMutator<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL.replace(/\/api\/v1$/, '')}${url}`, {
    ...init,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })

  const body = (await response.json().catch(() => null)) as EnvelopeBody | null
  if (!body || typeof body.code !== 'number') {
    throw new APIError(-1, `invalid response (${response.status})`, response.status)
  }
  if (body.code !== 0) {
    throw new APIError(body.code, body.message, response.status)
  }
  return { data: body, status: response.status, headers: response.headers } as T
}
