import { test, expect, helpers } from './fixtures'

/**
 * Guards against the home shell shrinking vertically (transparent band at bottom
 * over the fixed background). Regression for flex layout under <main>.
 */
test.describe('Home viewport shell', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/')
    await helpers.waitForPageReady(page)
    await page.waitForTimeout(300)
  })

  test('main fills viewport height', async ({ page }) => {
    const m = await page.evaluate(() => {
      const el = document.querySelector('main')
      const r = el?.getBoundingClientRect()
      return {
        innerHeight: window.innerHeight,
        mainHeight: r?.height ?? 0,
        mainTop: r?.top ?? 0,
      }
    })
    expect(Math.abs(m.mainTop)).toBeLessThan(4)
    expect(Math.abs(m.mainHeight - m.innerHeight)).toBeLessThan(6)
  })

  test('desktop sidebar bottom aligns with viewport (no large gap)', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 })
    await page.reload()
    await helpers.waitForPageReady(page)
    await page.waitForTimeout(300)

    const m = await page.evaluate(() => {
      const aside = document.querySelector('aside')
      const r = aside?.getBoundingClientRect()
      return {
        innerHeight: window.innerHeight,
        asideBottom: r?.bottom ?? 0,
      }
    })
    const gapPx = m.innerHeight - m.asideBottom
    expect(m.asideBottom).toBeGreaterThan(100)
    expect(gapPx).toBeLessThan(28)
  })

  test('chat composer strip near bottom after New Chat', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 })
    await page.reload()
    await helpers.waitForPageReady(page)
    await page.waitForTimeout(300)

    await page.getByRole('button', { name: 'New Chat' }).first().click()
    await page.locator('textarea').first().waitFor({ state: 'visible', timeout: 15000 })

    const m = await page.evaluate(() => {
      const ta = document.querySelector('textarea')
      const r = ta?.getBoundingClientRect()
      return {
        innerHeight: window.innerHeight,
        inputBottom: r?.bottom ?? 0,
      }
    })
    const gapBelowInput = m.innerHeight - m.inputBottom
    expect(gapBelowInput).toBeLessThan(120)
  })
})
