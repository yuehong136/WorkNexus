import { expect, test, type Page } from '@playwright/test'

// The default locale is zh-CN, so assertions use the zh copy. Specs run serially
// (workers: 1); auth.spec seeds setup first, so here the owner already exists.
const owner = {
  email: 'e2e-owner@example.com',
  password: 'e2e-owner-pass-123',
  displayName: 'E2E Owner',
}

const member = {
  email: 'e2e-proj-member@example.com',
  password: 'e2e-proj-member-pass-123',
  displayName: 'E2E Proj Member',
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

test('create a project and manage its members', async ({ page, browser }) => {
  await ensureOwnerLoggedIn(page)

  // A second user must exist before they can be added to a project: invite one
  // to the seed project, then activate the account in a fresh session.
  await page.getByRole('link', { name: '设置' }).click()
  await page.getByRole('link', { name: '成员' }).click()
  await page.getByRole('button', { name: '邀请成员' }).click()
  await page.getByLabel('邮箱').fill(member.email)
  await page.getByRole('button', { name: '生成邀请链接' }).click()
  const inviteLink = await page.locator('input[readonly]').inputValue()
  await page.getByRole('button', { name: '完成' }).click()

  const inviteeContext = await browser.newContext()
  const inviteePage = await inviteeContext.newPage()
  await inviteePage.goto(inviteLink)
  await inviteePage.getByLabel('显示名称').fill(member.displayName)
  await inviteePage.getByLabel('密码', { exact: true }).fill(member.password)
  await inviteePage.getByLabel('确认密码').fill(member.password)
  await inviteePage.getByRole('button', { name: '激活并登录' }).click()
  await expect(inviteePage.getByRole('button', { name: new RegExp(member.displayName) })).toBeVisible()
  await inviteeContext.close()

  // Create a project from the projects list (exact: the settings sub-nav also has a 我的项目 link).
  await page.getByRole('link', { name: '项目', exact: true }).click()
  await expect(page).toHaveURL(/\/projects$/)
  await page.getByRole('button', { name: '创建项目' }).click()
  await page.getByLabel('名称').fill('E2E Project')
  await page.getByLabel('标识 (Key)').fill('E2EP')
  await page.getByRole('button', { name: '创建', exact: true }).click()

  // Create navigates to the new project's detail page.
  await expect(page).toHaveURL(/\/projects\/[a-f0-9]+$/)
  await expect(page.getByRole('heading', { name: 'E2E Project' })).toBeVisible()

  // Add the invited user as a member.
  await page.getByRole('button', { name: '添加成员' }).click()
  await page.getByLabel('用户').selectOption({ label: `${member.displayName} (${member.email})` })
  await page.getByRole('button', { name: '添加', exact: true }).click()
  await expect(page.getByText(member.email)).toBeVisible()

  // Change the member's role, then remove them.
  await page.getByLabel('角色').selectOption('viewer')
  await expect(page.getByLabel('角色')).toHaveValue('viewer')

  await page.getByRole('button', { name: '移除' }).click()
  await page.getByRole('button', { name: '确认' }).click()
  await expect(page.getByText('暂无成员')).toBeVisible()
})
