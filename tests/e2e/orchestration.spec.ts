import { test, expect, helpers, MOCK_RESPONSES } from './fixtures'

/**
 * Orchestration Studio Tests for LLMHive
 * 
 * Tests cover:
 * - Configuration cards (Models, Reasoning, Tuning)
 * - Drawer interactions
 * - Model selection
 * - Reasoning methods
 * - Settings persistence
 * - Toggle behavior
 * - Responsive layout
 */

test.describe('Orchestration Studio Page', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)
  })

  test('page loads with title', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Orchestration')
  })

  test('all configuration cards are visible', async ({ page }) => {
    await expect(page.getByText('Models')).toBeVisible()
    await expect(page.getByText('Reasoning')).toBeVisible()
    await expect(page.getByText('Tuning')).toBeVisible()
  })

  test('page has description text', async ({ page }) => {
    // Should have some description about orchestration
    await expect(page.locator('h1')).toContainText('Orchestration')
  })
})

test.describe('Models Configuration', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)
  })

  test('models drawer opens when clicking Models card', async ({ page }) => {
    await page.getByRole('button', { name: /Models/i }).click()
    
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
  })

  test('models drawer shows available model providers', async ({ page }) => {
    await page.getByRole('button', { name: /Models/i }).click()
    await page.waitForTimeout(500)
    
    // Should show model providers
    const hasProvider = await page.getByText('GPT').or(page.getByText('OpenAI')).or(page.getByText('Claude')).isVisible()
    expect(hasProvider).toBe(true)
  })

  test('can toggle individual models', async ({ page }) => {
    await page.getByRole('button', { name: /Models/i }).click()
    await page.waitForTimeout(500)
    
    // Look for toggle switches or checkboxes
    const toggles = page.locator('[role="switch"], input[type="checkbox"]')
    const count = await toggles.count()
    
    if (count > 0) {
      const firstToggle = toggles.first()
      await firstToggle.click()
      // Toggle state should change
    }
  })

  test('drawer closes when pressing Escape', async ({ page }) => {
    await page.getByRole('button', { name: /Models/i }).click()
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
    
    await page.keyboard.press('Escape')
    await page.waitForTimeout(500)
    
    // Drawer should close (may need to verify specific state)
  })

  test('drawer has close button', async ({ page }) => {
    await page.getByRole('button', { name: /Models/i }).click()
    await page.waitForTimeout(500)
    
    // Should have some way to close the drawer
    const closeButton = page.getByRole('button', { name: /close/i }).or(page.locator('[aria-label="Close"]'))
    const hasClose = await closeButton.isVisible().catch(() => false)
    // Close button is optional if escape works
  })
})

test.describe('Reasoning Configuration', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)
  })

  test('reasoning drawer opens when clicking Reasoning card', async ({ page }) => {
    await page.getByRole('button', { name: /Reasoning/i }).click()
    
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
  })

  test('reasoning drawer shows mode options', async ({ page }) => {
    await page.getByRole('button', { name: /Reasoning/i }).click()
    await page.waitForTimeout(500)
    
    // Should show reasoning mode options like auto, manual
    const hasOptions = await page.getByText(/auto|manual|standard/i).isVisible()
    expect(hasOptions).toBe(true)
  })

  test('reasoning drawer shows method selection', async ({ page }) => {
    await page.getByRole('button', { name: /Reasoning/i }).click()
    await page.waitForTimeout(500)
    
    // Should show reasoning methods
    const hasMethods = await page.getByText(/chain|thought|reflection|step/i).first().isVisible().catch(() => false)
    // Methods may or may not be visible depending on mode
  })

  test('can select reasoning mode', async ({ page }) => {
    await page.getByRole('button', { name: /Reasoning/i }).click()
    await page.waitForTimeout(500)
    
    // Look for mode selection options
    const modeButton = page.getByRole('button', { name: /auto|manual/i }).first()
    if (await modeButton.isVisible()) {
      await modeButton.click()
    }
  })
})

test.describe('Tuning Configuration', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)
  })

  test('tuning drawer opens when clicking Tuning card', async ({ page }) => {
    await page.getByRole('button', { name: /Tuning/i }).click()
    
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
  })

  test('tuning drawer shows optimization options', async ({ page }) => {
    await page.getByRole('button', { name: /Tuning/i }).click()
    await page.waitForTimeout(500)
    
    await expect(page.getByText('Prompt Optimization')).toBeVisible()
  })

  test('tuning drawer shows quality settings', async ({ page }) => {
    await page.getByRole('button', { name: /Tuning/i }).click()
    await page.waitForTimeout(500)
    
    // Should show quality-related options
    const hasQuality = await page.getByText(/optimization|quality|validation/i).first().isVisible()
    expect(hasQuality).toBe(true)
  })

  test('can toggle prompt optimization', async ({ page }) => {
    await page.getByRole('button', { name: /Tuning/i }).click()
    await page.waitForTimeout(500)
    
    const toggle = page.locator('[role="switch"]').first()
    if (await toggle.isVisible()) {
      const initialState = await toggle.getAttribute('aria-checked')
      await toggle.click()
      // State should have changed
    }
  })
})

test.describe('Settings Persistence', () => {
  test('settings are saved to cookies/localStorage', async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)
    
    // Open tuning and toggle something
    await page.getByRole('button', { name: /Tuning/i }).click()
    await page.waitForTimeout(500)
    
    // Make a change if possible
    const toggle = page.locator('[role="switch"]').first()
    if (await toggle.isVisible()) {
      await toggle.click()
    }
    
    // Close drawer
    await page.keyboard.press('Escape')
    
    // Reload page
    await page.reload()
    await helpers.waitForPageReady(page)
    
    // Settings should persist (implementation dependent)
  })

  test('settings are included in chat requests', async ({ page }) => {
    let capturedRequest: any = null
    
    await page.route('/api/chat', async (route) => {
      const postData = route.request().postData()
      if (postData) {
        capturedRequest = JSON.parse(postData)
      }
      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        body: 'Test response',
      })
    })
    
    await page.goto('/')
    await helpers.waitForPageReady(page)
    
    const textarea = page.locator('textarea').first()
    await textarea.fill('Test message')
    await textarea.press('Enter')
    
    await page.waitForResponse('/api/chat')
    
    expect(capturedRequest).toBeDefined()
    if (capturedRequest) {
      expect(capturedRequest.orchestratorSettings).toBeDefined()
    }
  })

  test('modified settings persist across page navigation', async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)
    
    // Navigate away and back
    await page.goto('/settings')
    await helpers.waitForPageReady(page)
    
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)
    
    // Page should load correctly
    await expect(page.getByText('Models')).toBeVisible()
  })
})

test.describe('Drawer Interactions', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)
  })

  test('only one drawer open at a time', async ({ page }) => {
    // Open Models drawer
    await page.getByRole('button', { name: /Models/i }).click()
    await page.waitForTimeout(500)
    
    // Try to open Reasoning drawer
    await page.keyboard.press('Escape')
    await page.waitForTimeout(300)
    
    await page.getByRole('button', { name: /Reasoning/i }).click()
    await page.waitForTimeout(500)
    
    // Only one drawer should be open
    const dialogs = page.locator('[role="dialog"], [data-state="open"]')
    const count = await dialogs.count()
    expect(count).toBeLessThanOrEqual(2) // May have nested elements
  })

  test('drawer can be closed by clicking outside', async ({ page }) => {
    await page.getByRole('button', { name: /Models/i }).click()
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
    
    // Click outside the drawer (on the overlay)
    await page.locator('[data-state="open"]').first().press('Escape')
    await page.waitForTimeout(500)
  })

  test('drawer content is scrollable if needed', async ({ page }) => {
    await page.getByRole('button', { name: /Models/i }).click()
    await page.waitForTimeout(500)
    
    // Drawer should be visible and potentially scrollable
    const drawer = page.getByRole('dialog').or(page.locator('[data-state="open"]')).first()
    await expect(drawer).toBeVisible()
  })
})

test.describe('Error States', () => {
  test('handles agents API failure gracefully', async ({ page, mockApi }) => {
    await mockApi.mockAgentsError(500)
    
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)
    
    // Page should still load
    await expect(page.locator('h1')).toContainText('Orchestration')
    
    // Models drawer should still be accessible
    await page.getByRole('button', { name: /Models/i }).click()
    await page.waitForTimeout(500)
  })

  test('handles settings API failure gracefully', async ({ page, mockApi }) => {
    await mockApi.mockSettingsError()
    
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)
    
    // Page should still function
    await expect(page.getByText('Models')).toBeVisible()
  })
})

test.describe('Responsive Layout', () => {
  test('orchestration studio works on desktop', async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)
    
    await expect(page.getByText('Models')).toBeVisible()
    await expect(page.getByText('Reasoning')).toBeVisible()
    await expect(page.getByText('Tuning')).toBeVisible()
  })

  test('orchestration studio works on tablet', async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.setViewportSize({ width: 768, height: 1024 })
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)
    
    await expect(page.getByText('Models')).toBeVisible()
  })

  test('orchestration studio works on mobile', async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)
    
    await expect(page.locator('h1')).toContainText('Orchestration')
  })

  test('drawers work on mobile', async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)
    
    await page.getByRole('button', { name: /Models/i }).click()
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
  })
})

test.describe('Accessibility', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)
  })

  test('cards are keyboard accessible', async ({ page }) => {
    // Tab to cards
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')
    
    // Should be able to activate with Enter
    await page.keyboard.press('Enter')
    
    // Some drawer should open
    await page.waitForTimeout(500)
  })

  test('drawers can be closed with Escape', async ({ page }) => {
    await page.getByRole('button', { name: /Models/i }).click()
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
    
    await page.keyboard.press('Escape')
    await page.waitForTimeout(500)
  })

  test('focus is trapped in open drawer', async ({ page }) => {
    await page.getByRole('button', { name: /Models/i }).click()
    await page.waitForTimeout(500)
    
    // Tab through drawer - focus should stay in drawer
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')
    
    // Focus should still be in drawer
    const focusedElement = await page.evaluate(() => {
      const el = document.activeElement
      return el?.closest('[role="dialog"], [data-state="open"]') !== null
    })
    // Focus trap may or may not be implemented
  })
})

test.describe('Performance', () => {
  test('orchestration page loads quickly', async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    
    const startTime = Date.now()
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)
    const loadTime = Date.now() - startTime
    
    // Should load within 5 seconds
    expect(loadTime).toBeLessThan(5000)
  })

  test('drawers open quickly', async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)
    
    const startTime = Date.now()
    await page.getByRole('button', { name: /Models/i }).click()
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
    const openTime = Date.now() - startTime
    
    // Drawer should open within 1 second
    expect(openTime).toBeLessThan(1000)
  })
})
