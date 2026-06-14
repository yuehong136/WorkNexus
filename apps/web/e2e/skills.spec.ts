import { expect, test, type Page } from '@playwright/test'

// Default locale is zh-CN. Specs run serially; this one self-seeds via the setup
// path when run in isolation, or logs in when auth.spec already created the owner.
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

test('skills center reflects the MCP catalog and shows the empty invocation log', async ({ page }) => {
  await ensureOwnerLoggedIn(page)

  await page.getByRole('link', { name: 'Skills / MCP' }).click()
  await expect(page).toHaveURL(/\/skills$/)
  await expect(page.getByRole('heading', { name: 'Skills / MCP', level: 1 })).toBeVisible()

  // Reflected from the composed MCP server (namespace -> skill).
  await expect(page.getByText('workitem-skill')).toBeVisible()
  await expect(page.getByText('workitem_get_work_item')).toBeVisible()

  // No AI calls have happened yet in the e2e database.
  await expect(page.getByText('暂无调用记录')).toBeVisible()
})
