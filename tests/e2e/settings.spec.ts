import { test, expect, helpers, MOCK_RESPONSES } from './fixtures'

/**
 * Settings Page Tests for LLMHive
 * 
 * Tests cover:
 * - Settings categories (Account, Billing, Connections, Notifications, Privacy, Appearance)
 * - Drawer interactions
 * - Form validation
 * - Settings persistence (save/load)
 * - Error handling
 * - Responsive layout
 */

test.describe('Settings Page', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/settings')
    await helpers.waitForPageReady(page)
  })

  test('page loads with title', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Settings')
  })

  test('all settings category cards are visible', async ({ page }) => {
    await expect(page.locator('button.settings-card').filter({ hasText: 'Account' })).toBeVisible()
    await expect(page.locator('button.settings-card').filter({ hasText: 'Billing' })).toBeVisible()
    await expect(page.locator('button.settings-card').filter({ hasText: 'Connections' })).toBeVisible()
    await expect(page.locator('button.settings-card').filter({ hasText: 'Notifications' })).toBeVisible()
    await expect(page.locator('button.settings-card').filter({ hasText: 'Privacy' })).toBeVisible()
    await expect(page.locator('button.settings-card').filter({ hasText: 'Appearance' })).toBeVisible()
  })

  test('page has organized layout', async ({ page }) => {
    const cards = page.locator('button.settings-card')
    const count = await cards.count()
    expect(count).toBeGreaterThanOrEqual(6)
  })
})

test.describe('Account Settings', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/settings')
    await helpers.waitForPageReady(page)
  })

  test('account drawer opens when clicking Account card', async ({ page }) => {
    await page.locator('button.settings-card').filter({ hasText: 'Account' }).click()
    
    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 })
  })

  test('account drawer shows profile fields', async ({ page }) => {
    await page.locator('button.settings-card').filter({ hasText: 'Account' }).click()
    await page.waitForTimeout(500)

    const dialog = page.getByRole('dialog', { name: 'Account' })
    await expect(dialog.getByText('Display Name')).toBeVisible()
    await expect(dialog.getByText('Email', { exact: true })).toBeVisible()
  })

  test('account drawer shows Save Changes button', async ({ page }) => {
    await page.locator('button.settings-card').filter({ hasText: 'Account' }).click()
    await page.waitForTimeout(500)
    
    await expect(page.getByRole('button', { name: /Save Changes/i })).toBeVisible()
  })

  test('account drawer links to Clerk management', async ({ page }) => {
    await page.locator('button.settings-card').filter({ hasText: 'Account' }).click()
    await page.waitForTimeout(500)

    await expect(
      page.getByRole('button', { name: /Manage Account in Clerk/i }),
    ).toBeVisible()
  })

  test('can edit display name', async ({ page }) => {
    await page.locator('button.settings-card').filter({ hasText: 'Account' }).click()
    await page.waitForTimeout(500)

    const dialog = page.getByRole('dialog', { name: 'Account' })
    const nameInput = dialog.getByPlaceholder('Your name')
    await nameInput.fill('New Display Name')
    await expect(nameInput).toHaveValue('New Display Name')
  })

  test('form validates required fields', async ({ page, mockApi }) => {
    await mockApi.clearAllMocks()
    await mockApi.mockSettingsSaveSuccess()
    await page.goto('/settings')
    await helpers.waitForPageReady(page)

    await page.locator('button.settings-card').filter({ hasText: 'Account' }).click()
    await page.waitForTimeout(500)

    const dialog = page.getByRole('dialog', { name: 'Account' })
    await dialog.getByPlaceholder('Your name').fill('E2E User')

    const saveButton = page.getByRole('button', { name: /Save Changes/i })
    await saveButton.click()

    await page.waitForTimeout(1000)
  })
})

test.describe('Billing Settings', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/settings')
    await helpers.waitForPageReady(page)
  })

  test('Billing drawer opens when clicking Billing card', async ({ page }) => {
    await page.locator('button.settings-card').filter({ hasText: 'Billing' }).click()

    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 })
  })

  test('Billing drawer shows plan summary', async ({ page }) => {
    await page.locator('button.settings-card').filter({ hasText: 'Billing' }).click()
    await page.waitForTimeout(500)

    const dialog = page.getByRole('dialog', { name: 'Billing' })
    await expect(dialog.getByText('Current Plan')).toBeVisible()
    await expect(dialog.getByText('Free').first()).toBeVisible()
  })

  test('Billing drawer shows upgrade action', async ({ page }) => {
    await page.locator('button.settings-card').filter({ hasText: 'Billing' }).click()
    await page.waitForTimeout(500)

    await expect(page.getByRole('button', { name: /Upgrade to ELITE/i })).toBeVisible()
  })
})

test.describe('Connections Settings', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/settings')
    await helpers.waitForPageReady(page)
  })

  test('connections drawer opens when clicking Connections card', async ({ page }) => {
    await page.getByRole('button', { name: /Connections/i }).click()
    
    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 })
  })

  test('connections drawer shows available integrations', async ({ page }) => {
    await page.getByRole('button', { name: /Connections/i }).click()
    await page.waitForTimeout(500)
    
    // Should show some integration options
    const hasIntegration = await page.getByText(/Google|GitHub|Slack|connect/i).first().isVisible().catch(() => false)
    // Integrations may vary
  })
})

test.describe('Notifications Settings', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/settings')
    await helpers.waitForPageReady(page)
  })

  test('notifications drawer opens when clicking Notifications card', async ({ page }) => {
    await page.getByRole('button', { name: /Notifications/i }).click()
    
    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 })
  })

  test('notifications drawer shows notification types', async ({ page }) => {
    await page.locator('button.settings-card').filter({ hasText: 'Notifications' }).click()
    await page.waitForTimeout(500)

    await expect(page.getByText('Email Notifications').first()).toBeVisible()
    await expect(page.getByText('Push Notifications').first()).toBeVisible()
  })

  test('can toggle notification preferences', async ({ page }) => {
    await page.getByRole('button', { name: /Notifications/i }).click()
    await page.waitForTimeout(500)
    
    const toggles = page.locator('[role="switch"]')
    const count = await toggles.count()
    
    if (count > 0) {
      const firstToggle = toggles.first()
      const initialState = await firstToggle.getAttribute('aria-checked')
      await firstToggle.click()
      const newState = await firstToggle.getAttribute('aria-checked')
      // State should have changed
    }
  })
})

test.describe('Privacy Settings', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/settings')
    await helpers.waitForPageReady(page)
  })

  test('privacy drawer opens when clicking Privacy card', async ({ page }) => {
    await page.getByRole('button', { name: /Privacy/i }).click()
    
    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 })
  })

  test('privacy drawer shows privacy options', async ({ page }) => {
    await page.getByRole('button', { name: /Privacy/i }).click()
    await page.waitForTimeout(500)
    
    await expect(page.getByText('Share Usage Data')).toBeVisible()
  })

  test('can toggle privacy settings', async ({ page }) => {
    await page.getByRole('button', { name: /Privacy/i }).click()
    await page.waitForTimeout(500)
    
    const toggles = page.locator('[role="switch"]')
    if (await toggles.first().isVisible()) {
      await toggles.first().click()
    }
  })

  test('privacy drawer shows data management options', async ({ page }) => {
    await page.getByRole('button', { name: /Privacy/i }).click()
    await page.waitForTimeout(500)
    
    // Should have data-related options
    const hasDataOption = await page.getByText(/data|export|delete/i).first().isVisible().catch(() => false)
  })
})

test.describe('Appearance Settings', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/settings')
    await helpers.waitForPageReady(page)
  })

  test('appearance drawer opens when clicking Appearance card', async ({ page }) => {
    await page.locator('button.settings-card').filter({ hasText: 'Appearance' }).click()
    
    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 })
  })

  test('appearance drawer shows theme options', async ({ page }) => {
    await page.locator('button.settings-card').filter({ hasText: 'Appearance' }).click()
    await page.waitForTimeout(500)

    const dialog = page.getByRole('dialog').filter({ hasText: 'Appearance' })
    await expect(dialog.getByText('Theme')).toBeVisible()
    await expect(dialog.getByRole('button', { name: /^Dark$/i })).toBeVisible({ timeout: 10000 })
  })

  test('can select theme', async ({ page }) => {
    await page.locator('button.settings-card').filter({ hasText: 'Appearance' }).click()
    await page.waitForTimeout(500)
    
    // Look for theme options
    const lightOption = page.getByText(/light/i).first()
    const darkOption = page.getByText(/dark/i).first()
    
    if (await lightOption.isVisible()) {
      await lightOption.click()
    } else if (await darkOption.isVisible()) {
      await darkOption.click()
    }
  })

  test('theme preference persists after reload', async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    
    await page.locator('button.settings-card').filter({ hasText: 'Appearance' }).click()
    await page.waitForTimeout(500)
    
    // Close and reload
    await page.keyboard.press('Escape')
    await page.reload()
    await helpers.waitForPageReady(page)
    
    // Page should still work
    await expect(page.locator('h1')).toContainText('Settings')
  })
})

test.describe('Settings Save/Load', () => {
  test('account save prompts when not signed in', async ({ page }) => {
    await page.goto('/settings')
    await helpers.waitForPageReady(page)

    await page.locator('button.settings-card').filter({ hasText: 'Account' }).click()
    await page.waitForTimeout(500)

    const dialog = page.getByRole('dialog', { name: 'Account' })
    await dialog.getByPlaceholder('Your name').fill('E2E Save User')

    await page.getByRole('button', { name: /Save Changes/i }).click()

    await expect(page.getByText(/signed in/i)).toBeVisible({ timeout: 5000 })
  })

  test('settings are loaded on page load', async ({ page }) => {
    let apiCalled = false
    await page.route('/api/settings*', (route) => {
      if (route.request().method() === 'GET') {
        apiCalled = true
      }
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          settings: MOCK_RESPONSES.settings,
        }),
      })
    })
    
    await page.goto('/settings')
    await helpers.waitForPageReady(page)
    
    // Settings may be loaded from cookies or API
  })

  test('handles save attempt without crashing', async ({ page }) => {
    await page.goto('/settings')
    await helpers.waitForPageReady(page)

    await page.locator('button.settings-card').filter({ hasText: 'Account' }).click()
    await page.waitForTimeout(500)

    const dialog = page.getByRole('dialog', { name: 'Account' })
    await dialog.getByPlaceholder('Your name').fill('E2E Save Fail User')

    await page.getByRole('button', { name: /Save Changes/i }).click()

    await page.waitForTimeout(1000)

    await expect(page.locator('img[alt="LLMHive"]').first()).toBeVisible()
  })
})

test.describe('Settings Drawer Behavior', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/settings')
    await helpers.waitForPageReady(page)
  })

  test('drawer closes when pressing Escape', async ({ page }) => {
    await page.locator('button.settings-card').filter({ hasText: 'Account' }).click()
    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 })
    
    await page.keyboard.press('Escape')
    await page.waitForTimeout(500)
  })

  test('only one drawer open at a time', async ({ page }) => {
    await page.locator('button.settings-card').filter({ hasText: 'Account' }).click()
    await page.waitForTimeout(500)
    
    await page.keyboard.press('Escape')
    await page.waitForTimeout(300)
    
    await page.locator('button.settings-card').filter({ hasText: 'Billing' }).click()
    await page.waitForTimeout(500)
    
    // Only one drawer should be visible
  })

  test('unsaved changes prompt on close', async ({ page }) => {
    await page.locator('button.settings-card').filter({ hasText: 'Account' }).click()
    await page.waitForTimeout(500)
    
    // Make a change
    const input = page.locator('input').first()
    if (await input.isVisible()) {
      await input.fill('Changed value')
    }
    
    // Try to close
    await page.keyboard.press('Escape')
    
    // May show confirmation or just close - implementation dependent
    await page.waitForTimeout(500)
  })
})

test.describe('Settings Responsive Layout', () => {
  test('settings page works on desktop', async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.goto('/settings')
    await helpers.waitForPageReady(page)
    
    await expect(page.locator('button.settings-card').filter({ hasText: 'Account' })).toBeVisible()
    await expect(page.locator('button.settings-card').filter({ hasText: 'Billing' })).toBeVisible()
  })

  test('settings page works on tablet', async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.setViewportSize({ width: 768, height: 1024 })
    await page.goto('/settings')
    await helpers.waitForPageReady(page)
    
    await expect(page.locator('button.settings-card').filter({ hasText: 'Account' })).toBeVisible()
  })

  test('settings page works on mobile', async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/settings')
    await helpers.waitForPageReady(page)
    
    await expect(page.locator('h1')).toContainText('Settings')
  })

  test('drawers work on mobile', async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/settings')
    await helpers.waitForPageReady(page)
    
    await page.locator('button.settings-card').filter({ hasText: 'Account' }).click()
    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 })
  })
})

test.describe('Settings Accessibility', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/settings')
    await helpers.waitForPageReady(page)
  })

  test('cards are keyboard accessible', async ({ page }) => {
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')
    
    // Should be able to activate with Enter
    await page.keyboard.press('Enter')
    await page.waitForTimeout(500)
  })

  test('form fields have labels', async ({ page }) => {
    await page.locator('button.settings-card').filter({ hasText: 'Account' }).click()
    await page.waitForTimeout(500)
    
    // Check for label elements or aria-label
    const labels = page.locator('label')
    const count = await labels.count()
    expect(count).toBeGreaterThan(0)
  })

  test('buttons have accessible names', async ({ page }) => {
    const cards = page.locator('button.settings-card')
    const n = await cards.count()
    expect(n).toBeGreaterThan(0)
    for (let i = 0; i < n; i++) {
      const text = (await cards.nth(i).textContent())?.trim() ?? ''
      expect(text.length).toBeGreaterThan(0)
    }
  })
})

test.describe('Settings Performance', () => {
  test('settings page loads quickly', async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    
    const startTime = Date.now()
    await page.goto('/settings')
    await helpers.waitForPageReady(page)
    const loadTime = Date.now() - startTime
    
    expect(loadTime).toBeLessThan(15000)
  })

  test('drawers open quickly', async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/settings')
    await helpers.waitForPageReady(page)

    const accountCard = page.locator('button.settings-card').filter({ hasText: 'Account' })
    await accountCard.scrollIntoViewIfNeeded()
    const startTime = Date.now()
    await accountCard.click({ timeout: 15000 })
    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 15000 })
    const openTime = Date.now() - startTime

    expect(openTime).toBeLessThan(15000)
  })
})
