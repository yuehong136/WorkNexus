import { expect, test } from '@playwright/test'

// The default locale is zh-CN, so assertions use the zh copy.
const owner = {
  email: 'e2e-owner@example.com',
  password: 'e2e-owner-pass-123',
  displayName: 'E2E Owner',
}

const member = {
  email: 'e2e-member@example.com',
  password: 'e2e-member-pass-123',
  displayName: 'E2E Member',
}

test('setup, logout, login and invite main path', async ({ page, browser }) => {
  // Fresh database: the root redirects to first-run setup.
  await page.goto('/')
  await expect(page).toHaveURL(/\/setup$/)

  await page.getByLabel('邮箱').fill(owner.email)
  await page.getByLabel('显示名称').fill(owner.displayName)
  await page.getByLabel('密码', { exact: true }).fill(owner.password)
  await page.getByLabel('确认密码').fill(owner.password)
  await page.getByRole('button', { name: '完成初始化' }).click()

  // Setup auto-logs-in and lands on the workbench with the user menu.
  const userMenu = page.getByRole('button', { name: new RegExp(owner.displayName) })
  await expect(userMenu).toBeVisible()

  // Logout returns to /login.
  await userMenu.click()
  await page.getByRole('menuitem', { name: '退出登录' }).click()
  await expect(page).toHaveURL(/\/login$/)

  // Login main path.
  await page.getByLabel('邮箱').fill(owner.email)
  await page.getByLabel('密码').fill(owner.password)
  await page.getByRole('button', { name: '登录' }).click()
  await expect(userMenu).toBeVisible()

  // Invite a member from the members page and copy the link.
  await page.getByRole('link', { name: '成员' }).click()
  await page.getByRole('button', { name: '邀请成员' }).click()
  await page.getByLabel('邮箱').fill(member.email)
  await page.getByRole('button', { name: '生成邀请链接' }).click()
  const inviteLink = await page.locator('input[readonly]').inputValue()
  expect(inviteLink).toContain('/invites/wn_inv_')
  await page.getByRole('button', { name: '完成' }).click()
  await expect(page.getByText('待接受')).toBeVisible()

  // The invitee opens the link in a fresh session and activates the account.
  const inviteeContext = await browser.newContext()
  const inviteePage = await inviteeContext.newPage()
  await inviteePage.goto(inviteLink)
  await inviteePage.getByLabel('显示名称').fill(member.displayName)
  await inviteePage.getByLabel('密码', { exact: true }).fill(member.password)
  await inviteePage.getByLabel('确认密码').fill(member.password)
  await inviteePage.getByRole('button', { name: '激活并登录' }).click()
  await expect(inviteePage.getByRole('button', { name: new RegExp(member.displayName) })).toBeVisible()
  await inviteeContext.close()
})
