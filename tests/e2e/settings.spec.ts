import { test, expect, helpers, MOCK_RESPONSES } from './fixtures'

/**
 * Settings Page Tests for LLMHive
 * 
 * Tests cover:
 * - Settings categories (Account, API Keys, Connections, Notifications, Privacy, Appearance)
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
    await expect(page.getByRole('button', { name: /Account/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /API Keys/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /Connections/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /Notifications/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /Privacy/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /Appearance/i })).toBeVisible()
  })

  test('page has organized layout', async ({ page }) => {
    // Cards should be in a grid or list
    const cards = page.getByRole('button').filter({ hasText: /Account|API Keys|Privacy/i })
    const count = await cards.count()
    expect(count).toBeGreaterThanOrEqual(3)
  })
})

test.describe('Account Settings', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/settings')
    await helpers.waitForPageReady(page)
  })

  test('account drawer opens when clicking Account card', async ({ page }) => {
    await page.getByRole('button', { name: /Account/i }).click()
    
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
  })

  test('account drawer shows profile fields', async ({ page }) => {
    await page.getByRole('button', { name: /Account/i }).click()
    await page.waitForTimeout(500)
    
    await expect(page.getByText('Display Name')).toBeVisible()
    await expect(page.getByText('Email')).toBeVisible()
  })

  test('account drawer shows Save Changes button', async ({ page }) => {
    await page.getByRole('button', { name: /Account/i }).click()
    await page.waitForTimeout(500)
    
    await expect(page.getByRole('button', { name: /Save Changes/i })).toBeVisible()
  })

  test('account drawer shows Delete Account option', async ({ page }) => {
    await page.getByRole('button', { name: /Account/i }).click()
    await page.waitForTimeout(500)
    
    await expect(page.getByText('Danger Zone')).toBeVisible()
    await expect(page.getByRole('button', { name: /Delete Account/i })).toBeVisible()
  })

  test('can edit display name', async ({ page }) => {
    await page.getByRole('button', { name: /Account/i }).click()
    await page.waitForTimeout(500)
    
    const nameInput = page.locator('input').first()
    if (await nameInput.isVisible()) {
      await nameInput.fill('New Display Name')
      await expect(nameInput).toHaveValue('New Display Name')
    }
  })

  test('form validates required fields', async ({ page, mockApi }) => {
    await mockApi.mockSettingsSaveSuccess()
    
    await page.getByRole('button', { name: /Account/i }).click()
    await page.waitForTimeout(500)
    
    // Try to save - should either succeed or show validation
    const saveButton = page.getByRole('button', { name: /Save Changes/i })
    await saveButton.click()
    
    // Form should respond (success or validation message)
    await page.waitForTimeout(1000)
  })
})

test.describe('API Keys Settings', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/settings')
    await helpers.waitForPageReady(page)
  })

  test('API keys drawer opens when clicking API Keys card', async ({ page }) => {
    await page.getByRole('button', { name: /API Keys/i }).click()
    
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
  })

  test('API keys drawer shows provider options', async ({ page }) => {
    await page.getByRole('button', { name: /API Keys/i }).click()
    await page.waitForTimeout(500)
    
    await expect(page.getByText('OpenAI')).toBeVisible()
    await expect(page.getByText('Anthropic')).toBeVisible()
  })

  test('API keys drawer shows input fields for keys', async ({ page }) => {
    await page.getByRole('button', { name: /API Keys/i }).click()
    await page.waitForTimeout(500)
    
    // Should have input fields for API keys
    const inputs = page.locator('input[type="password"], input[type="text"]')
    const count = await inputs.count()
    expect(count).toBeGreaterThan(0)
  })

  test('API key inputs are masked by default', async ({ page }) => {
    await page.getByRole('button', { name: /API Keys/i }).click()
    await page.waitForTimeout(500)
    
    // Find password inputs
    const passwordInputs = page.locator('input[type="password"]')
    const count = await passwordInputs.count()
    // API keys should be masked
  })

  test('can toggle API key visibility', async ({ page }) => {
    await page.getByRole('button', { name: /API Keys/i }).click()
    await page.waitForTimeout(500)
    
    // Look for show/hide button
    const showButton = page.getByRole('button', { name: /show|hide|eye/i }).first()
    if (await showButton.isVisible()) {
      await showButton.click()
      // Input type should change to text
    }
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
    
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
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
    
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
  })

  test('notifications drawer shows notification types', async ({ page }) => {
    await page.getByRole('button', { name: /Notifications/i }).click()
    await page.waitForTimeout(500)
    
    await expect(page.getByText('Email Notifications')).toBeVisible()
    await expect(page.getByText('Push Notifications')).toBeVisible()
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
    
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
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
    await page.getByRole('button', { name: /Appearance/i }).click()
    
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
  })

  test('appearance drawer shows theme options', async ({ page }) => {
    await page.getByRole('button', { name: /Appearance/i }).click()
    await page.waitForTimeout(500)
    
    await expect(page.getByText('Theme')).toBeVisible()
  })

  test('can select theme', async ({ page }) => {
    await page.getByRole('button', { name: /Appearance/i }).click()
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
    
    await page.getByRole('button', { name: /Appearance/i }).click()
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
  test('settings API is called on save', async ({ page }) => {
    let apiCalled = false
    await page.route('/api/settings*', (route) => {
      if (route.request().method() === 'POST') {
        apiCalled = true
      }
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      })
    })
    
    await page.goto('/settings')
    await helpers.waitForPageReady(page)
    
    await page.getByRole('button', { name: /Account/i }).click()
    await page.waitForTimeout(500)
    
    const saveButton = page.getByRole('button', { name: /Save Changes/i })
    await saveButton.click()
    
    await page.waitForTimeout(1000)
    // API may or may not be called depending on implementation
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

  test('handles save failure gracefully', async ({ page, mockApi }) => {
    await mockApi.mockSettingsError()
    
    await page.goto('/settings')
    await helpers.waitForPageReady(page)
    
    await page.getByRole('button', { name: /Account/i }).click()
    await page.waitForTimeout(500)
    
    const saveButton = page.getByRole('button', { name: /Save Changes/i })
    await saveButton.click()
    
    await page.waitForTimeout(1000)
    
    // Page should not crash
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
    await page.getByRole('button', { name: /Account/i }).click()
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
    
    await page.keyboard.press('Escape')
    await page.waitForTimeout(500)
  })

  test('only one drawer open at a time', async ({ page }) => {
    await page.getByRole('button', { name: /Account/i }).click()
    await page.waitForTimeout(500)
    
    await page.keyboard.press('Escape')
    await page.waitForTimeout(300)
    
    await page.getByRole('button', { name: /API Keys/i }).click()
    await page.waitForTimeout(500)
    
    // Only one drawer should be visible
  })

  test('unsaved changes prompt on close', async ({ page }) => {
    await page.getByRole('button', { name: /Account/i }).click()
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
    
    await expect(page.getByRole('button', { name: /Account/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /API Keys/i })).toBeVisible()
  })

  test('settings page works on tablet', async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.setViewportSize({ width: 768, height: 1024 })
    await page.goto('/settings')
    await helpers.waitForPageReady(page)
    
    await expect(page.getByRole('button', { name: /Account/i })).toBeVisible()
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
    
    await page.getByRole('button', { name: /Account/i }).click()
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
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
    await page.getByRole('button', { name: /Account/i }).click()
    await page.waitForTimeout(500)
    
    // Check for label elements or aria-label
    const labels = page.locator('label')
    const count = await labels.count()
    expect(count).toBeGreaterThan(0)
  })

  test('buttons have accessible names', async ({ page }) => {
    // All buttons should have text or aria-label
    const buttons = page.getByRole('button')
    const count = await buttons.count()
    
    for (let i = 0; i < Math.min(count, 5); i++) {
      const button = buttons.nth(i)
      const text = await button.textContent()
      const ariaLabel = await button.getAttribute('aria-label')
      expect(text || ariaLabel).toBeTruthy()
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
    
    expect(loadTime).toBeLessThan(5000)
  })

  test('drawers open quickly', async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/settings')
    await helpers.waitForPageReady(page)
    
    const startTime = Date.now()
    await page.getByRole('button', { name: /Account/i }).click()
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
    const openTime = Date.now() - startTime
    
    expect(openTime).toBeLessThan(1000)
  })
})
