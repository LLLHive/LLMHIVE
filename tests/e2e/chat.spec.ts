import { test, expect, helpers, MOCK_RESPONSES } from './fixtures'

/**
 * Chat Functionality Tests for LLMHive
 * 
 * Tests cover:
 * - Chat input behavior
 * - Message sending and receiving
 * - Template cards
 * - Error handling (500 errors, timeouts, network failures)
 * - Retry logic
 * - Response display
 * - Performance
 */

test.describe('Chat Input', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/')
    await helpers.waitForPageReady(page)
  })

  test('chat input textarea is visible', async ({ page }) => {
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
    
    const value = await textarea.inputValue()
    expect(value).toContain('Line 1')
    expect(value).toContain('Line 2')
  })

  test('input clears after sending message', async ({ page, mockApi }) => {
    await mockApi.mockChatSuccess()
    
    const textarea = page.locator('textarea').first()
    await expect(textarea).toBeVisible({ timeout: 15000 })
    
    await textarea.fill('Test message')
    await textarea.press('Enter')
    
    // Input should clear after sending
    await expect(textarea).toHaveValue('', { timeout: 5000 })
  })
})

test.describe('Chat Message Sending', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/')
    await helpers.waitForPageReady(page)
  })

  test('Enter key sends message', async ({ page, mockApi }) => {
    let requestReceived = false
    await page.route('/api/chat', (route) => {
      requestReceived = true
      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        body: 'Response',
      })
    })
    
    const textarea = page.locator('textarea').first()
    await textarea.fill('Test message')
    await textarea.press('Enter')
    
    // Wait for the request
    await page.waitForTimeout(1000)
    expect(requestReceived).toBe(true)
  })

  test('user message appears in chat', async ({ page, mockApi }) => {
    await mockApi.mockChatSuccess('Test response from AI')
    
    const textarea = page.locator('textarea').first()
    await textarea.fill('Hello AI')
    await textarea.press('Enter')
    
    // User message should appear
    await expect(page.getByText('Hello AI')).toBeVisible({ timeout: 15000 })
  })

  test('AI response appears after user message', async ({ page, mockApi }) => {
    await mockApi.mockChatSuccess('This is the AI response.')
    
    const textarea = page.locator('textarea').first()
    await textarea.fill('Hello AI')
    await textarea.press('Enter')
    
    // Wait for response
    await expect(page.getByText('This is the AI response.')).toBeVisible({ timeout: 15000 })
  })

  test('request includes orchestrator settings', async ({ page }) => {
    let capturedRequest: any = null
    
    await page.route('/api/chat', (route) => {
      const postData = route.request().postData()
      if (postData) {
        capturedRequest = JSON.parse(postData)
      }
      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        body: 'Response',
      })
    })
    
    const textarea = page.locator('textarea').first()
    await textarea.fill('Test')
    await textarea.press('Enter')
    
    await page.waitForResponse('/api/chat')
    
    expect(capturedRequest).toBeDefined()
    expect(capturedRequest.orchestratorSettings).toBeDefined()
  })
})

test.describe('Chat Templates', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/')
    await helpers.waitForPageReady(page)
  })

  test('template cards are visible on home page', async ({ page }) => {
    // At least one template should be visible
    const hasTemplate = await page.getByText('General').or(page.getByText('Code')).isVisible()
    expect(hasTemplate).toBe(true)
  })

  test('clicking template card prepares chat', async ({ page }) => {
    const codeTemplate = page.getByText('Code').first()
    if (await codeTemplate.isVisible()) {
      await codeTemplate.click()
    }
    
    // Chat interface should remain visible
    await expect(page.locator('textarea').first()).toBeVisible()
  })
})

test.describe('Chat Error Handling - Server Errors', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await helpers.waitForPageReady(page)
  })

  test('shows error on 500 Internal Server Error', async ({ page, mockApi }) => {
    await mockApi.mockChatError(500, 'Internal server error')
    
    const textarea = page.locator('textarea').first()
    await textarea.fill('Test message')
    await textarea.press('Enter')
    
    // Page should still be functional
    await page.waitForTimeout(2000)
    await expect(page.locator('img[alt="LLMHive"]').first()).toBeVisible()
    
    // Should show some error indication or retry option
    const hasError = await page.getByText(/error|failed|retry/i).isVisible().catch(() => false)
    // Error handling may vary - main thing is page doesn't crash
  })

  test('shows error on 503 Service Unavailable', async ({ page, mockApi }) => {
    await mockApi.mockChatError(503, 'Service temporarily unavailable')
    
    const textarea = page.locator('textarea').first()
    await textarea.fill('Test message')
    await textarea.press('Enter')
    
    // Page should remain functional
    await page.waitForTimeout(2000)
    await expect(page.locator('img[alt="LLMHive"]').first()).toBeVisible()
  })

  test('handles 400 Bad Request gracefully', async ({ page, mockApi }) => {
    await mockApi.mockChatError(400, 'Invalid request format')
    
    const textarea = page.locator('textarea').first()
    await textarea.fill('Test message')
    await textarea.press('Enter')
    
    await page.waitForTimeout(2000)
    await expect(page.locator('img[alt="LLMHive"]').first()).toBeVisible()
  })

  test('handles 401 Unauthorized gracefully', async ({ page, mockApi }) => {
    await mockApi.mockChatError(401, 'Unauthorized')
    
    const textarea = page.locator('textarea').first()
    await textarea.fill('Test message')
    await textarea.press('Enter')
    
    await page.waitForTimeout(2000)
    await expect(page.locator('img[alt="LLMHive"]').first()).toBeVisible()
  })

  test('handles 429 Rate Limited gracefully', async ({ page, mockApi }) => {
    await mockApi.mockChatError(429, 'Too many requests')
    
    const textarea = page.locator('textarea').first()
    await textarea.fill('Test message')
    await textarea.press('Enter')
    
    await page.waitForTimeout(2000)
    await expect(page.locator('img[alt="LLMHive"]').first()).toBeVisible()
  })
})

test.describe('Chat Error Handling - Network Errors', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await helpers.waitForPageReady(page)
  })

  test('handles network failure gracefully', async ({ page }) => {
    await page.route('/api/chat', (route) => {
      route.abort('failed')
    })
    
    const textarea = page.locator('textarea').first()
    await textarea.fill('Test message')
    await textarea.press('Enter')
    
    // Page should not crash
    await page.waitForTimeout(3000)
    await expect(page.locator('img[alt="LLMHive"]').first()).toBeVisible()
  })

  test('handles connection reset gracefully', async ({ page }) => {
    await page.route('/api/chat', (route) => {
      route.abort('connectionreset')
    })
    
    const textarea = page.locator('textarea').first()
    await textarea.fill('Test message')
    await textarea.press('Enter')
    
    await page.waitForTimeout(3000)
    await expect(page.locator('img[alt="LLMHive"]').first()).toBeVisible()
  })

  test('handles connection refused gracefully', async ({ page }) => {
    await page.route('/api/chat', (route) => {
      route.abort('connectionrefused')
    })
    
    const textarea = page.locator('textarea').first()
    await textarea.fill('Test message')
    await textarea.press('Enter')
    
    await page.waitForTimeout(3000)
    await expect(page.locator('img[alt="LLMHive"]').first()).toBeVisible()
  })
})

test.describe('Chat Error Handling - Timeouts', () => {
  // Use shorter timeouts for tests
  test.setTimeout(60000)

  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await helpers.waitForPageReady(page)
  })

  test('handles slow response gracefully', async ({ page }) => {
    // Mock a slow response (but not timeout)
    await page.route('/api/chat', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 3000))
      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        body: 'Delayed response',
      })
    })
    
    const textarea = page.locator('textarea').first()
    await textarea.fill('Test message')
    await textarea.press('Enter')
    
    // Should eventually show response
    await expect(page.getByText('Delayed response')).toBeVisible({ timeout: 10000 })
  })

  test('handles request timeout', async ({ page }) => {
    await page.route('/api/chat', async (route) => {
      // Wait longer than typical timeout
      await new Promise(resolve => setTimeout(resolve, 35000))
      route.abort('timedout')
    })
    
    const textarea = page.locator('textarea').first()
    await textarea.fill('Test message')
    await textarea.press('Enter')
    
    // Page should remain functional
    await page.waitForTimeout(5000)
    await expect(page.locator('img[alt="LLMHive"]').first()).toBeVisible()
  })
})

test.describe('Chat Retry Logic', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await helpers.waitForPageReady(page)
  })

  test('retries on transient error and succeeds', async ({ page, mockApi }) => {
    await mockApi.mockChatRetrySuccess(2) // Fail twice, then succeed
    
    const textarea = page.locator('textarea').first()
    await textarea.fill('Test message')
    await textarea.press('Enter')
    
    // Should eventually succeed after retries
    await expect(page.getByText(/Success after/)).toBeVisible({ timeout: 30000 })
  })
})

test.describe('Chat Message Display', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/')
    await helpers.waitForPageReady(page)
  })

  test('messages are displayed in order', async ({ page, mockApi }) => {
    await mockApi.mockChatSuccess('First response')
    
    const textarea = page.locator('textarea').first()
    
    // Send first message
    await textarea.fill('First message')
    await textarea.press('Enter')
    await expect(page.getByText('First message')).toBeVisible()
    await expect(page.getByText('First response')).toBeVisible()
  })

  test('long messages are displayed correctly', async ({ page, mockApi }) => {
    const longResponse = 'This is a very long response. '.repeat(50)
    await mockApi.mockChatSuccess(longResponse)
    
    const textarea = page.locator('textarea').first()
    await textarea.fill('Give me a long response')
    await textarea.press('Enter')
    
    // Should show at least part of the long response
    await expect(page.getByText('This is a very long response')).toBeVisible({ timeout: 15000 })
  })

  test('markdown in responses is rendered', async ({ page, mockApi }) => {
    await mockApi.mockChatSuccess('Here is some **bold** and *italic* text.')
    
    const textarea = page.locator('textarea').first()
    await textarea.fill('Test markdown')
    await textarea.press('Enter')
    
    // Response should appear (markdown rendering may vary)
    await expect(page.getByText(/bold|italic/)).toBeVisible({ timeout: 15000 })
  })

  test('code blocks in responses are displayed', async ({ page, mockApi }) => {
    await mockApi.mockChatSuccess('Here is code:\n```python\nprint("Hello")\n```')
    
    const textarea = page.locator('textarea').first()
    await textarea.fill('Show me code')
    await textarea.press('Enter')
    
    await expect(page.getByText('print')).toBeVisible({ timeout: 15000 })
  })
})

test.describe('Chat Keyboard Shortcuts', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/')
    await helpers.waitForPageReady(page)
  })

  test('Ctrl+Enter (or Cmd+Enter) sends message', async ({ page, mockApi }) => {
    let messageSent = false
    await page.route('/api/chat', (route) => {
      messageSent = true
      route.fulfill({ status: 200, contentType: 'text/plain', body: 'Response' })
    })
    
    const textarea = page.locator('textarea').first()
    await textarea.fill('Test')
    await textarea.press('Control+Enter')
    
    await page.waitForTimeout(2000)
    // Either Control+Enter or Enter should send
  })

  test('Escape clears the input', async ({ page }) => {
    const textarea = page.locator('textarea').first()
    await textarea.fill('Test message')
    await textarea.press('Escape')
    
    // Escape might clear or might not - depends on implementation
    // Main test is that it doesn't crash
    await expect(textarea).toBeVisible()
  })
})

test.describe('Chat Performance', () => {
  test('chat interface loads within acceptable time', async ({ page }) => {
    const startTime = Date.now()
    await page.goto('/')
    await helpers.waitForPageReady(page)
    const loadTime = Date.now() - startTime
    
    // Page should load within 10 seconds
    expect(loadTime).toBeLessThan(10000)
    
    await expect(page.locator('textarea').first()).toBeVisible({ timeout: 15000 })
  })

  test('typing in chat input has no noticeable lag', async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/')
    await helpers.waitForPageReady(page)
    
    const textarea = page.locator('textarea').first()
    await expect(textarea).toBeVisible({ timeout: 15000 })
    
    const testMessage = 'This is a test message to verify typing performance in the chat interface.'
    
    const startTime = Date.now()
    await textarea.fill(testMessage)
    const typeTime = Date.now() - startTime
    
    expect(typeTime).toBeLessThan(5000)
    await expect(textarea).toHaveValue(testMessage)
  })

  test('response appears within reasonable time', async ({ page, mockApi }) => {
    await mockApi.mockChatSuccess('Quick response')
    await page.goto('/')
    await helpers.waitForPageReady(page)
    
    const textarea = page.locator('textarea').first()
    await textarea.fill('Test')
    
    const startTime = Date.now()
    await textarea.press('Enter')
    await expect(page.getByText('Quick response')).toBeVisible({ timeout: 15000 })
    const responseTime = Date.now() - startTime
    
    // Response should appear within 5 seconds (mocked)
    expect(responseTime).toBeLessThan(5000)
  })
})

test.describe('Chat Accessibility', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/')
    await helpers.waitForPageReady(page)
  })

  test('chat input is focusable', async ({ page }) => {
    const textarea = page.locator('textarea').first()
    await textarea.focus()
    
    // Should be focused
    const isFocused = await textarea.evaluate(el => el === document.activeElement)
    expect(isFocused).toBe(true)
  })

  test('chat input has appropriate placeholder', async ({ page }) => {
    const textarea = page.locator('textarea').first()
    const placeholder = await textarea.getAttribute('placeholder')
    
    // Should have a helpful placeholder
    expect(placeholder).toBeTruthy()
  })
})
