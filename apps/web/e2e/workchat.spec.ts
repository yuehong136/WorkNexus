import { expect, test, type Page } from '@playwright/test'

// Default locale is zh-CN. Specs run serially (workers: 1). The backend runs with
// WORKNEXUS_AI_CLIENT=fake, so a run streams a reply + proposes a create_work_item action.
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

test('WorkChat: send message -> AI proposes action -> approve -> work item persists', async ({ page }) => {
  await ensureOwnerLoggedIn(page)

  // Create a dedicated project and open its AI assistant.
  await page.getByRole('link', { name: '项目' }).click()
  await page.getByRole('button', { name: '创建项目' }).click()
  await page.getByLabel('名称').fill('E2E WorkChat')
  await page.getByLabel('标识 (Key)').fill('EWC')
  await page.getByRole('button', { name: '创建', exact: true }).click()
  await expect(page).toHaveURL(/\/projects\/[a-f0-9]+$/)
  await page.getByRole('button', { name: 'AI 助手' }).click()
  await expect(page).toHaveURL(/\/ai$/)
  await expect(page.getByRole('heading', { name: 'AI 助手', level: 1 })).toBeVisible()

  // Send a message; the fake AI streams a reply and proposes a work item.
  await page.getByPlaceholder('向 AI 描述需求，回车发送（Shift+回车换行）').fill('帮我建个跟进任务')
  await page.getByRole('button', { name: '发送' }).click()

  // The proposed-action card shows the pending create_work_item with its arguments.
  await expect(page.getByText('创建工作项')).toBeVisible()
  await expect(page.getByText('Follow up from WorkChat')).toBeVisible()
  await expect(page.getByText('待确认')).toBeVisible()

  // Approve: the backend double-checks and executes; the card leaves the pending list.
  await page.getByRole('button', { name: '批准' }).click()
  await expect(page.getByRole('button', { name: '批准' })).toBeHidden()

  // The work item now exists in the project (source=ai_chat).
  await page.getByRole('link', { name: '项目' }).click()
  await page.getByRole('link', { name: 'E2E WorkChat' }).click()
  await page.getByRole('button', { name: '工作项' }).click()
  await expect(page).toHaveURL(/\/work-items$/)
  await expect(page.getByText('Follow up from WorkChat')).toBeVisible()
})
