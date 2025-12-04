import { test, expect } from '@playwright/test'

test.describe('Chat Functionality', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('can start a new chat and see input area', async ({ page }) => {
    // Click template or new chat button to start
    await page.click('button:has-text("New Chat")')
    
    // Chat input should be visible
    const textarea = page.locator('textarea[placeholder*="Ask"]')
    await expect(textarea).toBeVisible()
    await expect(textarea).toBeEnabled()
  })

  test('can type in chat input', async ({ page }) => {
    await page.click('button:has-text("New Chat")')
    
    const textarea = page.locator('textarea[placeholder*="Ask"]')
    await textarea.fill('Hello, this is a test message')
    
    await expect(textarea).toHaveValue('Hello, this is a test message')
  })

  test('send button is disabled when input is empty', async ({ page }) => {
    await page.click('button:has-text("New Chat")')
    
    // Find send button (has Send icon)
    const sendButton = page.locator('button:has(svg.lucide-send)')
    
    // Should be disabled when empty
    await expect(sendButton).toBeDisabled()
  })

  test('send button enables when text is entered', async ({ page }) => {
    await page.click('button:has-text("New Chat")')
    
    const textarea = page.locator('textarea[placeholder*="Ask"]')
    await textarea.fill('Test message')
    
    const sendButton = page.locator('button:has(svg.lucide-send)')
    await expect(sendButton).toBeEnabled()
  })

  test('pressing Enter sends message (without Shift)', async ({ page }) => {
    await page.click('button:has-text("New Chat")')
    
    const textarea = page.locator('textarea[placeholder*="Ask"]')
    await textarea.fill('Test message')
    await textarea.press('Enter')
    
    // Should show the user message
    await expect(page.locator('text=Test message')).toBeVisible({ timeout: 5000 })
  })

  test('Shift+Enter creates new line instead of sending', async ({ page }) => {
    await page.click('button:has-text("New Chat")')
    
    const textarea = page.locator('textarea[placeholder*="Ask"]')
    await textarea.fill('Line 1')
    await textarea.press('Shift+Enter')
    await textarea.type('Line 2')
    
    // Should have multiline content
    await expect(textarea).toHaveValue('Line 1\nLine 2')
  })
})

test.describe('Chat Templates', () => {
  test('template cards are visible on home page', async ({ page }) => {
    await page.goto('/')
    
    // Should see template options
    await expect(page.locator('text=General Assistant')).toBeVisible()
    await expect(page.locator('text=Research & Deep Reasoning')).toBeVisible()
    await expect(page.locator('text=Code & Debug')).toBeVisible()
  })

  test('clicking template starts new chat with preset', async ({ page }) => {
    await page.goto('/')
    
    // Click a template
    await page.click('text=Code & Debug')
    
    // Should show chat interface
    await expect(page.locator('textarea[placeholder*="Ask"]')).toBeVisible()
  })
})

test.describe('Chat Error Handling', () => {
  test('shows error gracefully on API failure', async ({ page }) => {
    // Mock API to fail
    await page.route('/api/chat', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal server error' }),
      })
    })

    await page.goto('/')
    await page.click('button:has-text("New Chat")')
    
    const textarea = page.locator('textarea[placeholder*="Ask"]')
    await textarea.fill('Test message')
    await textarea.press('Enter')
    
    // Should show error message (not crash)
    await expect(page.locator('text=error').or(page.locator('text=apologize'))).toBeVisible({ 
      timeout: 15000 
    })
  })

  test('handles network timeout gracefully', async ({ page }) => {
    // Mock API to timeout
    await page.route('/api/chat', async (route) => {
      // Delay for 5 seconds then fail
      await new Promise(resolve => setTimeout(resolve, 5000))
      route.abort('timedout')
    })

    await page.goto('/')
    await page.click('button:has-text("New Chat")')
    
    const textarea = page.locator('textarea[placeholder*="Ask"]')
    await textarea.fill('Test message')
    await textarea.press('Enter')
    
    // Should show loading state
    await expect(page.locator('.animate-bounce')).toBeVisible()
    
    // Wait for error (with extended timeout)
    await expect(page.locator('text=error').or(page.locator('text=apologize'))).toBeVisible({ 
      timeout: 30000 
    })
  })
})

test.describe('Orchestration Status', () => {
  test('shows orchestration status during processing', async ({ page }) => {
    // Mock API to respond slowly
    await page.route('/api/chat', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 2000))
      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        headers: {
          'X-Models-Used': '["gpt-4o"]',
          'X-Tokens-Used': '100',
          'X-Latency-Ms': '1500',
        },
        body: 'This is a test response from the AI.',
      })
    })

    await page.goto('/')
    await page.click('button:has-text("New Chat")')
    
    const textarea = page.locator('textarea[placeholder*="Ask"]')
    await textarea.fill('Test message')
    await textarea.press('Enter')
    
    // Should show orchestration status
    await expect(page.locator('text=Orchestration').or(page.locator('.animate-bounce'))).toBeVisible()
  })
})
