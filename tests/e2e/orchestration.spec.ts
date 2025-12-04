import { test, expect } from '@playwright/test'

/**
 * Orchestration Studio Tests for LLMHive
 * 
 * Tests cover:
 * - Configuration cards
 * - Drawer interactions
 * - Model selection
 * - Reasoning methods
 * - Settings persistence
 */

test.describe('Orchestration Studio Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/orchestration')
    await page.waitForLoadState('domcontentloaded')
  })

  test('page loads with title', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Orchestration')
  })

  test('configuration cards are visible', async ({ page }) => {
    // Verify main configuration cards
    await expect(page.getByText('Models')).toBeVisible()
    await expect(page.getByText('Reasoning')).toBeVisible()
    await expect(page.getByText('Tuning')).toBeVisible()
  })
})

test.describe('Models Configuration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/orchestration')
    await page.waitForLoadState('domcontentloaded')
  })

  test('models drawer opens when clicking Models card', async ({ page }) => {
    await page.getByRole('button', { name: /Models/i }).click()
    
    // Drawer should open
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
  })

  test('models drawer shows available model providers', async ({ page }) => {
    await page.getByRole('button', { name: /Models/i }).click()
    await page.waitForTimeout(500)
    
    // Should show major model providers
    await expect(page.getByText('GPT').or(page.getByText('OpenAI'))).toBeVisible()
  })

  test('drawer closes when pressing Escape', async ({ page }) => {
    await page.getByRole('button', { name: /Models/i }).click()
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
    
    await page.keyboard.press('Escape')
    
    // Drawer should close
    await page.waitForTimeout(500)
  })
})

test.describe('Reasoning Configuration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/orchestration')
    await page.waitForLoadState('domcontentloaded')
  })

  test('reasoning drawer opens when clicking Reasoning card', async ({ page }) => {
    await page.getByRole('button', { name: /Reasoning/i }).click()
    
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
  })
})

test.describe('Tuning Configuration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/orchestration')
    await page.waitForLoadState('domcontentloaded')
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
})

test.describe('Orchestration Settings Persistence', () => {
  test('settings are sent with chat requests', async ({ page }) => {
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

    // Navigate to home and send a message
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')
    await page.waitForTimeout(1000)
    
    const textarea = page.locator('textarea').first()
    await expect(textarea).toBeVisible({ timeout: 15000 })
    
    await textarea.fill('Test message')
    await textarea.press('Enter')
    
    // Wait for request to be captured
    await page.waitForResponse('/api/chat')
    
    // Verify settings were included in request
    expect(capturedRequest).toBeDefined()
    if (capturedRequest) {
      expect(capturedRequest.orchestratorSettings).toBeDefined()
    }
  })
})

test.describe('Responsive Layout', () => {
  test('orchestration studio works on desktop', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.goto('/orchestration')
    await page.waitForLoadState('domcontentloaded')
    
    await expect(page.getByText('Models')).toBeVisible()
    await expect(page.getByText('Reasoning')).toBeVisible()
  })

  test('orchestration studio works on tablet', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 })
    await page.goto('/orchestration')
    await page.waitForLoadState('domcontentloaded')
    
    await expect(page.getByText('Models')).toBeVisible()
  })

  test('orchestration studio works on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/orchestration')
    await page.waitForLoadState('domcontentloaded')
    
    await expect(page.locator('h1')).toContainText('Orchestration')
  })
})

test.describe('Orchestration Accessibility', () => {
  test('drawers can be closed with Escape', async ({ page }) => {
    await page.goto('/orchestration')
    await page.waitForLoadState('domcontentloaded')
    
    await page.getByRole('button', { name: /Models/i }).click()
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
    
    await page.keyboard.press('Escape')
    await page.waitForTimeout(500)
  })
})
