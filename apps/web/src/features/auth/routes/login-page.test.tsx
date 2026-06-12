import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { beforeAll, describe, expect, it } from 'vitest'

import { LoginPage } from '@/features/auth/routes/login-page'
import { authKeys } from '@/lib/auth/keys'
import { paths } from '@/lib/paths'
import { initI18n } from '@/locales/i18n'
import { makeCurrentUserContext } from '@/test/factories'
import { API_BASE, envelope, server } from '@/test/server'

beforeAll(async () => {
  await initI18n('zh-CN')
})

function renderLoginPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createMemoryRouter([{ path: paths.login(), element: <LoginPage /> }], {
    initialEntries: [paths.login()],
  })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return queryClient
}

describe('LoginPage', () => {
  it('shows zod validation messages on empty submit', async () => {
    renderLoginPage()
    await userEvent.click(screen.getByRole('button', { name: '登录' }))
    expect(await screen.findByText('请输入有效的邮箱地址')).toBeInTheDocument()
    expect(screen.getByText('请输入密码')).toBeInTheDocument()
  })

  it('shows the mapped inline error for invalid credentials', async () => {
    server.use(
      http.post(`${API_BASE}/auth/login`, () =>
        HttpResponse.json({ code: 4002, message: 'invalid email or password' }),
      ),
    )
    renderLoginPage()
    await userEvent.type(screen.getByLabelText('邮箱'), 'owner@example.com')
    await userEvent.type(screen.getByLabelText('密码'), 'wrong-password')
    await userEvent.click(screen.getByRole('button', { name: '登录' }))
    expect(await screen.findByText('邮箱或密码错误')).toBeInTheDocument()
  })

  it('primes the me cache with the returned context on success', async () => {
    const context = makeCurrentUserContext()
    server.use(http.post(`${API_BASE}/auth/login`, () => HttpResponse.json(envelope(context))))
    const queryClient = renderLoginPage()
    await userEvent.type(screen.getByLabelText('邮箱'), 'owner@example.com')
    await userEvent.type(screen.getByLabelText('密码'), 'owner-pass-123')
    await userEvent.click(screen.getByRole('button', { name: '登录' }))
    await screen.findByRole('button', { name: '登录' })
    await expect
      .poll(() => queryClient.getQueryData(authKeys.me()))
      .toMatchObject({ user: { email: 'owner@example.com' } })
  })
})
