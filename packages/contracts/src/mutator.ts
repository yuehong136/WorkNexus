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

interface Envelope<T> {
  code: number
  message: string
  data: T
}

const BASE_URL =
  (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) || 'http://localhost:8200/api/v1'

export async function apiMutator<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL.replace(/\/api\/v1$/, '')}${url}`, {
    ...init,
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
