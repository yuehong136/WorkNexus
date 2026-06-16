import { expect, test, type Page } from '@playwright/test'

// Closes the M8 loop: an AI-proposed action shows on the workbench as a first-class
// "to confirm" item; after approval the audit page shows the full propose→execute chain,
// the workbench surfaces the AI-created work item, and settings shows the masked AI
// connection. Backend runs WORKNEXUS_AI_CLIENT=fake (deterministic create_work_item).
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

async function openProjectAi(page: Page, projectName: string) {
  await page.getByRole('link', { name: '项目' }).click()
  await page.getByRole('link', { name: projectName }).click()
  await page.getByRole('button', { name: 'AI 助手' }).click()
  await expect(page).toHaveURL(/\/ai$/)
}

test('workbench surfaces pending AI action; audit shows the full chain; settings masks the connection', async ({
  page,
}) => {
  await ensureOwnerLoggedIn(page)

  // A dedicated project + an AI-proposed work item (pending).
  await page.getByRole('link', { name: '项目' }).click()
  await page.getByRole('button', { name: '创建项目' }).click()
  await page.getByLabel('名称').fill('E2E Home')
  await page.getByLabel('标识 (Key)').fill('EHM')
  await page.getByRole('button', { name: '创建', exact: true }).click()
  await expect(page).toHaveURL(/\/projects\/[a-f0-9]+$/)
  await page.getByRole('button', { name: 'AI 助手' }).click()
  await expect(page).toHaveURL(/\/ai$/)

  await page.getByPlaceholder('向 AI 描述需求，回车发送（Shift+回车换行）').fill('帮我建个跟进任务')
  await page.getByRole('button', { name: '发送' }).click()
  await expect(page.getByText('待确认')).toBeVisible()

  // Workbench: the pending AI action is a first-class card.
  await page.getByRole('link', { name: '工作台' }).click()
  await expect(page.getByRole('heading', { name: '工作台', level: 1 })).toBeVisible()
  const pendingCard = page.locator('section').filter({ hasText: '待确认 AI 动作' })
  await expect(pendingCard.getByRole('link').first()).toBeVisible()

  // Approve back on the AI page → the action executes.
  await openProjectAi(page, 'E2E Home')
  await page.getByRole('button', { name: '批准' }).click()
  await expect(page.getByRole('button', { name: '批准' })).toBeHidden()

  // Audit: the full propose → execute chain is recorded (action cells are buttons —
  // matched by role to avoid the hidden filter <option> of the same text).
  await page.getByRole('link', { name: '审计日志' }).click()
  await expect(page.getByRole('button', { name: 'ai.proposed_action.create' }).first()).toBeVisible()
  await expect(page.getByRole('button', { name: 'agent_action.execute' }).first()).toBeVisible()

  // Workbench again: the AI-created work item shows under "recently AI-created".
  await page.getByRole('link', { name: '工作台' }).click()
  await expect(page.getByText('Follow up from WorkChat').first()).toBeVisible()

  // Settings: the AI connection is shown masked (client is the deterministic fake here).
  await page.getByRole('link', { name: '设置' }).click()
  await page.getByRole('link', { name: 'AI 连接' }).click()
  await expect(page).toHaveURL(/\/settings\/ai$/)
  await expect(page.getByRole('heading', { name: 'AI 连接' })).toBeVisible()
  await expect(page.getByText('fake').first()).toBeVisible()
})
