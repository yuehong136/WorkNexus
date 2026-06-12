import { APIError } from '@worknexus/contracts/mutator'

// Single APIError class for the whole app: the orval mutator throws it, so
// re-export rather than redefine — two classes would break instanceof checks.
export { APIError }

interface Envelope<T> {
  code: number
  message: string
  data: T
}

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8200/api/v1'

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })

  const body = (await response.json().catch(() => null)) as Envelope<T> | null
  if (!body) {
    throw new APIError(-1, `invalid response (${response.status})`, response.status)
  }
  if (body.code !== 0) {
    throw new APIError(body.code, body.message, response.status)
  }
  return body.data
}

type EnvelopePayload<R> = R extends { status: 200; data: { data?: infer D } } ? NonNullable<D> : never

/** Unwrap an orval-generated response down to the envelope payload. The error
 * variants in the generated union never reach here — the mutator throws
 * APIError on any non-zero envelope code. */
export function unwrap<R extends { status: number; data: unknown }>(response: R): EnvelopePayload<R> {
  const payload = (response.data as { data?: unknown } | null)?.data
  if (payload == null) {
    throw new APIError(-1, 'empty response payload', response.status)
  }
  return payload as EnvelopePayload<R>
}

export function isAPIError(error: unknown, code?: number): error is APIError {
  return error instanceof APIError && (code === undefined || error.code === code)
}
