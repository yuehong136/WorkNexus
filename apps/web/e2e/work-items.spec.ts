import { expect, test, type Page } from '@playwright/test'

// Default locale is zh-CN. Specs run serially (workers: 1); auth.spec seeds the owner
// first, so here the owner already exists and we just log in.
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

test('work item lifecycle: create, comment, transition, board drag', async ({ page }) => {
  await ensureOwnerLoggedIn(page)

  // Create a dedicated project, then open its work items.
  await page.getByRole('link', { name: '项目' }).click()
  await page.getByRole('button', { name: '创建项目' }).click()
  await page.getByLabel('名称').fill('E2E Items')
  await page.getByLabel('标识 (Key)').fill('EIT')
  await page.getByRole('button', { name: '创建', exact: true }).click()
  await expect(page).toHaveURL(/\/projects\/[a-f0-9]+$/)
  await page.getByRole('button', { name: '工作项' }).click()
  await expect(page).toHaveURL(/\/work-items$/)

  // Create a work item from the list.
  await page.getByRole('button', { name: '新建工作项' }).click()
  await page.getByLabel('标题').fill('Drag me')
  await page.getByRole('button', { name: '创建', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Drag me' })).toBeVisible()

  // Open the drawer, add a comment.
  await page.getByRole('button', { name: 'Drag me' }).click()
  const drawer = page.getByRole('dialog')
  await expect(drawer.getByText('EIT-1')).toBeVisible()
  await drawer.getByPlaceholder('写下评论（支持 Markdown）').fill('Looks good')
  await drawer.getByRole('button', { name: '发表评论' }).click()
  await expect(drawer.getByText('Looks good')).toBeVisible()

  // Transition backlog -> todo via the drawer; the activity timeline records it.
  await drawer.getByRole('combobox').selectOption({ label: '待办' })
  await expect(drawer.getByText('流转了状态')).toBeVisible()

  // Close the drawer and open the board.
  await page.keyboard.press('Escape')
  await page.getByRole('button', { name: '看板视图' }).click()
  await expect(page).toHaveURL(/\/board$/)

  // The card now sits in the 待办 (todo) column; drag it to 进行中 (in_progress).
  const todoCard = page.locator('[data-status="todo"]').getByText('Drag me')
  await expect(todoCard).toBeVisible()
  const cardBox = await todoCard.boundingBox()
  const targetBox = await page.locator('[data-status="in_progress"]').boundingBox()
  if (!cardBox || !targetBox) throw new Error('missing bounding boxes for drag')

  await page.mouse.move(cardBox.x + cardBox.width / 2, cardBox.y + cardBox.height / 2)
  await page.mouse.down()
  await page.mouse.move(cardBox.x + cardBox.width / 2 + 12, cardBox.y + cardBox.height / 2, { steps: 6 })
  await page.mouse.move(targetBox.x + targetBox.width / 2, targetBox.y + targetBox.height / 2, { steps: 12 })
  await page.mouse.move(targetBox.x + targetBox.width / 2, targetBox.y + targetBox.height / 2 + 4, { steps: 4 })
  await page.mouse.up()

  await expect(page.locator('[data-status="in_progress"]').getByText('Drag me')).toBeVisible()
})
