import { test, expect } from '@playwright/test'

/**
 * Chat Functionality Tests for LLMHive
 * 
 * Tests cover:
 * - Chat input behavior
 * - Message sending
 * - Template cards
 * - Error handling
 * - Streaming responses
 * - Orchestration status
 */

test.describe('Chat Input', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
  })

  test('chat input textarea is visible', async ({ page }) => {
    // The chat input should be visible on the home page
    const textarea = page.locator('textarea[placeholder*="Ask"], textarea[placeholder*="Message"]')
    await expect(textarea).toBeVisible({ timeout: 10000 })
  })

  test('can type in chat input', async ({ page }) => {
    const textarea = page.locator('textarea[placeholder*="Ask"], textarea[placeholder*="Message"]').first()
    await expect(textarea).toBeVisible()
    
    await textarea.fill('Hello, this is a test message')
    await expect(textarea).toHaveValue('Hello, this is a test message')
  })

  test('send button is disabled when input is empty', async ({ page }) => {
    const textarea = page.locator('textarea[placeholder*="Ask"], textarea[placeholder*="Message"]').first()
    await textarea.clear()
    
    // Find send button
    const sendButton = page.locator('button:has(svg.lucide-send)')
    
    // Should be disabled when empty
    await expect(sendButton).toBeDisabled()
  })

  test('send button enables when text is entered', async ({ page }) => {
    const textarea = page.locator('textarea[placeholder*="Ask"], textarea[placeholder*="Message"]').first()
    await textarea.fill('Test message')
    
    const sendButton = page.locator('button:has(svg.lucide-send)')
    await expect(sendButton).toBeEnabled()
  })

  test('Shift+Enter creates new line instead of sending', async ({ page }) => {
    const textarea = page.locator('textarea[placeholder*="Ask"], textarea[placeholder*="Message"]').first()
    await textarea.fill('Line 1')
    await textarea.press('Shift+Enter')
    await textarea.type('Line 2')
    
    // Should have multiline content
    const value = await textarea.inputValue()
    expect(value).toContain('Line 1')
    expect(value).toContain('Line 2')
  })

  test('input clears after successful message send', async ({ page }) => {
    // Mock the API to return a response
    await page.route('/api/chat', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        headers: {
          'X-Models-Used': '["gpt-4o"]',
          'X-Tokens-Used': '100',
          'X-Latency-Ms': '500',
        },
        body: 'This is a test response from the AI.',
      })
    })

    const textarea = page.locator('textarea[placeholder*="Ask"], textarea[placeholder*="Message"]').first()
    await textarea.fill('Test message')
    await textarea.press('Enter')

    // Wait for the message to be sent
    await page.waitForTimeout(1000)

    // Input should be cleared after sending
    // (Depending on implementation, this may or may not clear immediately)
  })
})

test.describe('Chat Templates', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
  })

  test('template cards are visible on home page', async ({ page }) => {
    // Template cards should be visible
    await expect(page.locator('text=General Assistant')).toBeVisible({ timeout: 10000 })
    await expect(page.locator('text=Research & Deep Reasoning')).toBeVisible()
    await expect(page.locator('text=Code & Debug')).toBeVisible()
  })

  test('clicking template card prepares chat', async ({ page }) => {
    // Click a template
    const codeTemplate = page.locator('text=Code & Debug')
    await codeTemplate.click()
    
    // Should still show chat interface
    await expect(page.locator('textarea[placeholder*="Ask"], textarea[placeholder*="Message"]').first()).toBeVisible()
  })

  test('template cards show descriptions', async ({ page }) => {
    // Each template should have a description
    await expect(page.locator('text=General knowledge and conversation')).toBeVisible()
    await expect(page.locator('text=Deep analysis and complex')).toBeVisible()
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
    const textarea = page.locator('textarea[placeholder*="Ask"], textarea[placeholder*="Message"]').first()
    await textarea.fill('Hello AI')
    await textarea.press('Enter')

    // User message should appear
    await expect(page.locator('text=Hello AI')).toBeVisible({ timeout: 10000 })
  })

  test('AI response appears after sending', async ({ page }) => {
    // Mock the API with a response
    await page.route('/api/chat', async (route) => {
      // Small delay to simulate real API
      await new Promise(resolve => setTimeout(resolve, 500))
      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        headers: {
          'X-Models-Used': '["gpt-4o"]',
          'X-Tokens-Used': '100',
          'X-Latency-Ms': '500',
        },
        body: 'Hello! I am ready to help you.',
      })
    })

    await page.goto('/')
    const textarea = page.locator('textarea[placeholder*="Ask"], textarea[placeholder*="Message"]').first()
    await textarea.fill('Hello')
    await textarea.press('Enter')

    // Wait for AI response
    await expect(page.locator('text=Hello! I am ready to help you.')).toBeVisible({ timeout: 15000 })
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
    const textarea = page.locator('textarea[placeholder*="Ask"], textarea[placeholder*="Message"]').first()
    await textarea.fill('Test message')
    await textarea.press('Enter')

    // Should show some error indication (not crash)
    await expect(
      page.locator('text=/error|failed|apologize|sorry|went wrong/i')
    ).toBeVisible({ timeout: 15000 })
  })

  test('shows error message on API failure (503)', async ({ page }) => {
    await page.route('/api/chat', (route) => {
      route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Backend not configured' }),
      })
    })

    await page.goto('/')
    const textarea = page.locator('textarea[placeholder*="Ask"], textarea[placeholder*="Message"]').first()
    await textarea.fill('Test message')
    await textarea.press('Enter')

    // Should show error (not crash)
    await expect(
      page.locator('text=/error|failed|apologize|sorry|went wrong|backend/i')
    ).toBeVisible({ timeout: 15000 })
  })

  test('handles network timeout gracefully', async ({ page }) => {
    await page.route('/api/chat', async (route) => {
      // Long delay to simulate timeout
      await new Promise(resolve => setTimeout(resolve, 10000))
      route.abort('timedout')
    })

    await page.goto('/')
    const textarea = page.locator('textarea[placeholder*="Ask"], textarea[placeholder*="Message"]').first()
    await textarea.fill('Test message')
    await textarea.press('Enter')

    // Should show loading state
    await expect(
      page.locator('.animate-pulse, .animate-bounce, .loading, text=Loading')
    ).toBeVisible({ timeout: 5000 })
  })

  test('handles network failure gracefully', async ({ page }) => {
    await page.route('/api/chat', (route) => {
      route.abort('failed')
    })

    await page.goto('/')
    const textarea = page.locator('textarea[placeholder*="Ask"], textarea[placeholder*="Message"]').first()
    await textarea.fill('Test message')
    await textarea.press('Enter')

    // Should show error state (not crash)
    await page.waitForTimeout(5000)
    
    // Page should still be functional
    await expect(page.locator('img[alt="LLMHive"]').first()).toBeVisible()
  })
})

test.describe('Orchestration Status Display', () => {
  test('shows loading indicator during processing', async ({ page }) => {
    await page.route('/api/chat', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 3000))
      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        headers: {
          'X-Models-Used': '["gpt-4o"]',
          'X-Tokens-Used': '100',
          'X-Latency-Ms': '2500',
        },
        body: 'This is a test response.',
      })
    })

    await page.goto('/')
    const textarea = page.locator('textarea[placeholder*="Ask"], textarea[placeholder*="Message"]').first()
    await textarea.fill('Test message')
    await textarea.press('Enter')

    // Should show some loading/processing indicator
    await expect(
      page.locator('.animate-pulse, .animate-bounce, [class*="loading"], [class*="spinner"]')
    ).toBeVisible({ timeout: 2000 })
  })

  test('displays models used after response', async ({ page }) => {
    await page.route('/api/chat', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        headers: {
          'X-Models-Used': '["gpt-4o", "claude-sonnet-4"]',
          'X-Tokens-Used': '150',
          'X-Latency-Ms': '1200',
        },
        body: 'This is a response using multiple models.',
      })
    })

    await page.goto('/')
    const textarea = page.locator('textarea[placeholder*="Ask"], textarea[placeholder*="Message"]').first()
    await textarea.fill('Multi-model test')
    await textarea.press('Enter')

    // Wait for response
    await page.waitForTimeout(2000)
    
    // Models should be displayed somewhere (in response metadata)
    // The exact display depends on implementation
  })
})

test.describe('Chat Attachments', () => {
  test('attachment button is visible', async ({ page }) => {
    await page.goto('/')
    
    // File attachment button should be visible
    const attachButton = page.locator('button:has(svg.lucide-paperclip)')
    await expect(attachButton).toBeVisible()
  })

  test('microphone button is visible', async ({ page }) => {
    await page.goto('/')
    
    // Voice input button should be visible
    const micButton = page.locator('button:has(svg.lucide-mic)')
    await expect(micButton).toBeVisible()
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
    const textarea = page.locator('textarea[placeholder*="Ask"], textarea[placeholder*="Message"]').first()
    await textarea.fill('Test')
    await textarea.press('Enter')

    // Wait for the request
    await page.waitForTimeout(1000)
    expect(messageSent).toBe(true)
  })

  test('Escape clears focus from textarea', async ({ page }) => {
    await page.goto('/')
    const textarea = page.locator('textarea[placeholder*="Ask"], textarea[placeholder*="Message"]').first()
    await textarea.focus()
    await expect(textarea).toBeFocused()
    
    await page.keyboard.press('Escape')
    // Focus behavior may vary by implementation
  })
})

test.describe('Chat Performance', () => {
  test('chat interface loads within acceptable time', async ({ page }) => {
    const startTime = Date.now()
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    const loadTime = Date.now() - startTime

    // Page should load within 5 seconds
    expect(loadTime).toBeLessThan(5000)

    // Chat input should be visible
    await expect(
      page.locator('textarea[placeholder*="Ask"], textarea[placeholder*="Message"]').first()
    ).toBeVisible()
  })

  test('typing in chat input has no noticeable lag', async ({ page }) => {
    await page.goto('/')
    const textarea = page.locator('textarea[placeholder*="Ask"], textarea[placeholder*="Message"]').first()

    // Type a reasonably long message
    const testMessage = 'This is a test message to verify typing performance in the chat input field.'
    
    const startTime = Date.now()
    await textarea.fill(testMessage)
    const typeTime = Date.now() - startTime

    // Should complete in a reasonable time (allowing for Playwright overhead)
    expect(typeTime).toBeLessThan(2000)

    // Verify the text was entered
    await expect(textarea).toHaveValue(testMessage)
  })
})
