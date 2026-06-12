import { setupServer } from 'msw/node'

export const server = setupServer()

export const API_BASE = 'http://localhost:8200/api/v1'

export function envelope<T>(data: T) {
  return { code: 0, message: 'ok', data }
}
