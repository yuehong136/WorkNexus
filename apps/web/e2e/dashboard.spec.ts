import { expect, test, type Page } from '@playwright/test'

// Default locale is zh-CN. Specs run serially (workers: 1); auth.spec seeds the owner first.
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

async function createWorkItem(page: Page, title: string) {
  await page.getByRole('button', { name: '工作项' }).click()
  await expect(page).toHaveURL(/\/work-items$/)
  await page.getByRole('button', { name: '新建工作项' }).click()
  await page.getByLabel('标题').fill(title)
  await page.getByRole('button', { name: '创建', exact: true }).click()
  await expect(page.getByRole('button', { name: title })).toBeVisible()
  await page.getByRole('link', { name: '返回项目' }).click()
  await expect(page).toHaveURL(/\/projects\/[a-f0-9]+$/)
}

function totalValue(page: Page) {
  return page.locator('div.rounded-lg', { hasText: '工作项总数' }).locator('div.text-2xl')
}

test('dashboard reflects real data and updates as work items are created', async ({ page }) => {
  await ensureOwnerLoggedIn(page)

  await page.getByRole('link', { name: '项目' }).click()
  await page.getByRole('button', { name: '创建项目' }).click()
  await page.getByLabel('名称').fill('E2E Dashboard')
  await page.getByLabel('标识 (Key)').fill('EDB')
  await page.getByRole('button', { name: '创建', exact: true }).click()
  await expect(page).toHaveURL(/\/projects\/[a-f0-9]+$/)

  await createWorkItem(page, 'Dashboard One')

  // Open the project dashboard via the gated entry button.
  await page.getByRole('button', { name: '仪表盘' }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
  await expect(page.getByRole('heading', { name: '项目仪表盘' })).toBeVisible()
  await expect(totalValue(page)).toHaveText('1')
  // distribution charts + AI insight panel render
  await expect(page.getByText('状态分布')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'AI 洞察' })).toBeVisible()

  // Create a second work item; the dashboard count updates from real data.
  await page.getByRole('link', { name: '返回项目' }).click()
  await createWorkItem(page, 'Dashboard Two')
  await page.getByRole('button', { name: '仪表盘' }).click()
  await expect(totalValue(page)).toHaveText('2')
})
