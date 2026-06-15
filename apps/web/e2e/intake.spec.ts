import { expect, test, type Page } from '@playwright/test'

// Default locale is zh-CN. Specs run serially (workers: 1); auth.spec seeds the owner first,
// so here the owner already exists and we just log in.
const owner = {
  email: 'e2e-owner@example.com',
  password: 'e2e-owner-pass-123',
  displayName: 'E2E Owner',
}

async function ensureOwnerLoggedIn(page: Page) {
  await page.goto('/')
  await page.waitForURL(/\/(setup|login)$/)
  if (/\/setup$/.test(page.url())) {
    await page.getByLabel('邮箱').fill(owner.email)
    await page.getByLabel('显示名称').fill(owner.displayName)
    await page.getByLabel('密码', { exact: true }).fill(owner.password)
    await page.getByLabel('确认密码').fill(owner.password)
    await page.getByRole('button', { name: '完成初始化' }).click()
  } else {
    await page.getByLabel('邮箱').fill(owner.email)
    await page.getByLabel('密码').fill(owner.password)
    await page.getByRole('button', { name: '登录' }).click()
  }
  await expect(page.getByRole('button', { name: new RegExp(owner.displayName) })).toBeVisible()
}

test('intake lifecycle: submit, triage, accept-and-convert to work item', async ({ page }) => {
  await ensureOwnerLoggedIn(page)

  // Dedicated project, then open its intake pool.
  await page.getByRole('link', { name: '项目' }).click()
  await page.getByRole('button', { name: '创建项目' }).click()
  await page.getByLabel('名称').fill('E2E Intake')
  await page.getByLabel('标识 (Key)').fill('EIN')
  await page.getByRole('button', { name: '创建', exact: true }).click()
  await expect(page).toHaveURL(/\/projects\/[a-f0-9]+$/)
  await page.getByRole('button', { name: '请求池' }).click()
  await expect(page).toHaveURL(/\/intake$/)

  // Submit a manual request; the rule engine fills in advisory suggestions.
  await page.getByRole('button', { name: '新建请求' }).click()
  await page.getByLabel('标题').fill('登录页面崩溃 crash')
  await page.getByRole('button', { name: '创建', exact: true }).click()
  await expect(page.getByRole('button', { name: '登录页面崩溃 crash' })).toBeVisible()

  // Open the detail drawer and accept-and-convert.
  await page.getByRole('button', { name: '登录页面崩溃 crash' }).click()
  const drawer = page.getByRole('dialog')
  await expect(drawer.getByText('AI 分诊建议')).toBeVisible()
  await drawer.getByRole('button', { name: '接受', exact: true }).click()

  // The convert dialog is prefilled from the suggestion; confirm it.
  await page.getByRole('button', { name: '接受并转化' }).click()

  // The request is now converted (status badge in the table, not the filter <option>),
  // and the work item exists in the project.
  await expect(page.locator('table').getByText('已转化')).toBeVisible()
  await page.getByRole('link', { name: '返回项目' }).click()
  await page.getByRole('button', { name: '工作项' }).click()
  await expect(page).toHaveURL(/\/work-items$/)
  await expect(page.getByRole('button', { name: '登录页面崩溃 crash' })).toBeVisible()
})
