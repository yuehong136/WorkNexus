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

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8200/api/v1'

interface Envelope<T> {
  code: number
  message: string
  data: T
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
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
