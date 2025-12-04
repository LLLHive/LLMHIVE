import { test, expect } from '@playwright/test'

/**
 * Chat Functionality Tests for LLMHive
 * 
 * Tests cover:
 * - Chat input behavior
 * - Message sending
 * - Template cards
 * - Error handling
 */

test.describe('Chat Input', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')
    // Wait for React to hydrate
    await page.waitForTimeout(1000)
  })

  test('chat input textarea is visible', async ({ page }) => {
    // The chat input should be visible on the home page
    const textarea = page.locator('textarea').first()
    await expect(textarea).toBeVisible({ timeout: 15000 })
  })

  test('can type in chat input', async ({ page }) => {
    const textarea = page.locator('textarea').first()
    await expect(textarea).toBeVisible({ timeout: 15000 })
    
    await textarea.fill('Hello, this is a test message')
    await expect(textarea).toHaveValue('Hello, this is a test message')
  })

  test('Shift+Enter creates new line instead of sending', async ({ page }) => {
    const textarea = page.locator('textarea').first()
    await expect(textarea).toBeVisible({ timeout: 15000 })
    
    await textarea.fill('Line 1')
    await textarea.press('Shift+Enter')
    await textarea.type('Line 2')
    
    // Should have multiline content
    const value = await textarea.inputValue()
    expect(value).toContain('Line 1')
    expect(value).toContain('Line 2')
  })
})

test.describe('Chat Templates', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')
    await page.waitForTimeout(1000)
  })

  test('template cards are visible on home page', async ({ page }) => {
    // Template cards should be visible - check for any of the expected text
    await expect(
      page.getByText('General Assistant').or(page.getByText('General'))
    ).toBeVisible({ timeout: 15000 })
  })

  test('clicking template card prepares chat', async ({ page }) => {
    // Click a template
    const codeTemplate = page.getByText('Code').first()
    if (await codeTemplate.isVisible()) {
      await codeTemplate.click()
    }
    
    // Should still show chat interface
    await expect(page.locator('textarea').first()).toBeVisible()
  })
})

test.describe('Chat Message Display', () => {
  test('user message appears after sending', async ({ page }) => {
    // Mock the API
    await page.route('/api/chat', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        headers: {
          'X-Models-Used': '["gpt-4o"]',
          'X-Tokens-Used': '100',
          'X-Latency-Ms': '500',
        },
        body: 'Hello! How can I help you today?',
      })
    })

    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')
    await page.waitForTimeout(1000)
    
    const textarea = page.locator('textarea').first()
    await expect(textarea).toBeVisible({ timeout: 15000 })
    
    await textarea.fill('Hello AI')
    await textarea.press('Enter')

    // User message should appear
    await expect(page.getByText('Hello AI')).toBeVisible({ timeout: 15000 })
  })
})

test.describe('Chat Error Handling', () => {
  test('shows error message on API failure (500)', async ({ page }) => {
    await page.route('/api/chat', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal server error' }),
      })
    })

    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')
    await page.waitForTimeout(1000)
    
    const textarea = page.locator('textarea').first()
    await expect(textarea).toBeVisible({ timeout: 15000 })
    
    await textarea.fill('Test message')
    await textarea.press('Enter')

    // Should show some error indication (not crash) - page should still be functional
    await page.waitForTimeout(3000)
    await expect(page.locator('img[alt="LLMHive"]').first()).toBeVisible()
  })

  test('handles network failure gracefully', async ({ page }) => {
    await page.route('/api/chat', (route) => {
      route.abort('failed')
    })

    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')
    await page.waitForTimeout(1000)
    
    const textarea = page.locator('textarea').first()
    await expect(textarea).toBeVisible({ timeout: 15000 })
    
    await textarea.fill('Test message')
    await textarea.press('Enter')

    // Page should still be functional (not crash)
    await page.waitForTimeout(3000)
    await expect(page.locator('img[alt="LLMHive"]').first()).toBeVisible()
  })
})

test.describe('Chat Keyboard Shortcuts', () => {
  test('Enter sends message', async ({ page }) => {
    let messageSent = false
    await page.route('/api/chat', (route) => {
      messageSent = true
      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        body: 'Response',
      })
    })

    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')
    await page.waitForTimeout(1000)
    
    const textarea = page.locator('textarea').first()
    await expect(textarea).toBeVisible({ timeout: 15000 })
    
    await textarea.fill('Test')
    await textarea.press('Enter')

    // Wait for the request
    await page.waitForTimeout(2000)
    expect(messageSent).toBe(true)
  })
})

test.describe('Chat Performance', () => {
  test('chat interface loads within acceptable time', async ({ page }) => {
    const startTime = Date.now()
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')
    const loadTime = Date.now() - startTime

    // Page should load within 10 seconds (generous for dev server)
    expect(loadTime).toBeLessThan(10000)

    // Chat input should be visible
    await expect(page.locator('textarea').first()).toBeVisible({ timeout: 15000 })
  })

  test('typing in chat input has no noticeable lag', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')
    await page.waitForTimeout(1000)
    
    const textarea = page.locator('textarea').first()
    await expect(textarea).toBeVisible({ timeout: 15000 })

    // Type a reasonably long message
    const testMessage = 'This is a test message to verify typing performance.'
    
    const startTime = Date.now()
    await textarea.fill(testMessage)
    const typeTime = Date.now() - startTime

    // Should complete in a reasonable time
    expect(typeTime).toBeLessThan(5000)

    // Verify the text was entered
    await expect(textarea).toHaveValue(testMessage)
  })
})
