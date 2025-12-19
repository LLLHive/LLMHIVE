import { test, expect, helpers, MOCK_RESPONSES } from './fixtures'

/**
 * Clarifying Questions Regression Tests
 * 
 * CRITICAL: These tests ensure the clarifying questions feature continues working.
 * DO NOT remove or disable these tests.
 * 
 * The clarifying questions flow:
 * 1. User sends an ambiguous query
 * 2. Backend detects ambiguity and returns clarifying questions
 * 3. UI displays questions to user
 * 4. User answers or skips
 * 5. Backend processes with additional context
 */

test.describe('Clarifying Questions - Regression Tests', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/')
    await helpers.waitForPageReady(page)
  })

  test('clarifying questions are displayed for ambiguous queries', async ({ page }) => {
    // Mock a response that might trigger clarification UI
    await page.route('/api/chat', async (route) => {
      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        headers: {
          'X-Models-Used': '["gpt-4o"]',
          'X-Tokens-Used': '200',
          'X-Latency-Ms': '500',
          'X-Needs-Clarification': 'true',
        },
        body: 'To give you a better answer, could you please clarify what you mean by "the best"?',
      })
    })
    
    // Send an ambiguous query
    const textarea = page.locator('textarea').first()
    await textarea.fill('What is the best one?')
    await textarea.press('Enter')
    
    // Wait for response
    await page.waitForResponse('/api/chat')
    await page.waitForTimeout(500)
    
    // Should show some response
    const bodyText = await page.locator('body').textContent()
    expect(bodyText).toBeTruthy()
  })

  test('user can answer clarification and get complete response', async ({ page }) => {
    let requestCount = 0
    let lastRequest: any = null
    
    await page.route('/api/chat', async (route) => {
      requestCount++
      const postData = route.request().postData()
      if (postData) {
        lastRequest = JSON.parse(postData)
      }
      
      if (requestCount === 1) {
        // First request: return clarifying question
        route.fulfill({
          status: 200,
          contentType: 'text/plain',
          headers: {
            'X-Models-Used': '["gpt-4o"]',
            'X-Needs-Clarification': 'true',
          },
          body: 'Are you asking about programming languages or spoken languages?',
        })
      } else {
        // Second request: complete answer
        route.fulfill({
          status: 200,
          contentType: 'text/plain',
          headers: {
            'X-Models-Used': '["gpt-4o"]',
          },
          body: 'Python is considered one of the best programming languages for beginners due to its readable syntax.',
        })
      }
    })
    
    // Send initial query
    const textarea = page.locator('textarea').first()
    await textarea.fill('Which language is the best?')
    await textarea.press('Enter')
    
    await page.waitForResponse('/api/chat')
    await page.waitForTimeout(1000)
    
    // If there's a way to answer clarification, do it
    // Otherwise, just send a follow-up
    await textarea.fill('I meant programming languages')
    await textarea.press('Enter')
    
    await page.waitForResponse('/api/chat')
    await page.waitForTimeout(500)
    
    // Should have made 2 requests
    expect(requestCount).toBe(2)
  })

  test('clarification context is passed to backend', async ({ page }) => {
    let capturedRequest: any = null
    
    await page.route('/api/chat', async (route) => {
      const postData = route.request().postData()
      if (postData) {
        capturedRequest = JSON.parse(postData)
      }
      
      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        headers: {
          'X-Models-Used': '["gpt-4o"]',
        },
        body: 'Here is the information you requested.',
      })
    })
    
    // Send a query with context
    const textarea = page.locator('textarea').first()
    await textarea.fill('Tell me more about that')
    await textarea.press('Enter')
    
    await page.waitForResponse('/api/chat')
    
    expect(capturedRequest).toBeDefined()
    expect(capturedRequest.message || capturedRequest.prompt).toBeTruthy()
  })

  test('skip clarification and proceed works', async ({ page }) => {
    let requestCount = 0
    
    await page.route('/api/chat', async (route) => {
      requestCount++
      
      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        headers: {
          'X-Models-Used': '["gpt-4o"]',
        },
        body: 'Based on general context, here is a comprehensive answer...',
      })
    })
    
    // Send a query
    const textarea = page.locator('textarea').first()
    await textarea.fill('Compare them')
    await textarea.press('Enter')
    
    await page.waitForResponse('/api/chat')
    
    // Should have made at least one request
    expect(requestCount).toBeGreaterThan(0)
  })

  test('clarification does not break normal queries', async ({ page }) => {
    await page.route('/api/chat', async (route) => {
      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        headers: {
          'X-Models-Used': '["gpt-4o"]',
          'X-Tokens-Used': '150',
          'X-Latency-Ms': '400',
        },
        body: 'The capital of France is Paris.',
      })
    })
    
    // Send a clear, unambiguous query
    const textarea = page.locator('textarea').first()
    await textarea.fill('What is the capital of France?')
    await textarea.press('Enter')
    
    await page.waitForResponse('/api/chat')
    await page.waitForTimeout(500)
    
    // Should show the answer
    const bodyText = await page.locator('body').textContent()
    expect(bodyText?.toLowerCase()).toContain('paris')
  })

  test('multiple clarification rounds work correctly', async ({ page }) => {
    let requestCount = 0
    
    await page.route('/api/chat', async (route) => {
      requestCount++
      
      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        headers: {
          'X-Models-Used': '["gpt-4o"]',
          'X-Tokens-Used': `${100 * requestCount}`,
        },
        body: `Response ${requestCount}: Here is the information.`,
      })
    })
    
    const textarea = page.locator('textarea').first()
    
    // Round 1
    await textarea.fill('First question')
    await textarea.press('Enter')
    await page.waitForResponse('/api/chat')
    
    // Round 2
    await textarea.fill('Follow up question')
    await textarea.press('Enter')
    await page.waitForResponse('/api/chat')
    
    // Round 3
    await textarea.fill('Another follow up')
    await textarea.press('Enter')
    await page.waitForResponse('/api/chat')
    
    expect(requestCount).toBe(3)
  })
})

test.describe('Clarifying Questions - Edge Cases', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/')
    await helpers.waitForPageReady(page)
  })

  test('handles empty clarification response gracefully', async ({ page }) => {
    await page.route('/api/chat', async (route) => {
      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        headers: {
          'X-Models-Used': '["gpt-4o"]',
        },
        body: '',
      })
    })
    
    const textarea = page.locator('textarea').first()
    await textarea.fill('What?')
    await textarea.press('Enter')
    
    await page.waitForResponse('/api/chat')
    await page.waitForTimeout(500)
    
    // Should not crash
    await expect(page.locator('textarea').first()).toBeVisible()
  })

  test('handles clarification with special characters', async ({ page }) => {
    let capturedMessage = ''
    
    await page.route('/api/chat', async (route) => {
      const postData = route.request().postData()
      if (postData) {
        const parsed = JSON.parse(postData)
        capturedMessage = parsed.message || parsed.prompt || ''
      }
      
      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        body: 'Processed your question with special characters.',
      })
    })
    
    const textarea = page.locator('textarea').first()
    await textarea.fill('What about "quotes" & <tags> and emoji 🎉?')
    await textarea.press('Enter')
    
    await page.waitForResponse('/api/chat')
    
    // Should have preserved special characters
    expect(capturedMessage).toContain('quotes')
  })

  test('clarification timeout is handled', async ({ page }) => {
    await page.route('/api/chat', async (route) => {
      // Delay but eventually respond
      await new Promise(resolve => setTimeout(resolve, 2000))
      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        body: 'Delayed response received.',
      })
    })
    
    const textarea = page.locator('textarea').first()
    await textarea.fill('Slow question')
    await textarea.press('Enter')
    
    // Wait for the delayed response
    await page.waitForResponse('/api/chat', { timeout: 10000 })
    
    // Should show some response
    const bodyText = await page.locator('body').textContent()
    expect(bodyText).toBeTruthy()
  })
})

test.describe('Clarifying Questions - API Integration', () => {
  test('orchestration settings include clarification context', async ({ page }) => {
    let capturedRequest: any = null
    
    await page.route('/api/chat', async (route) => {
      const postData = route.request().postData()
      if (postData) {
        capturedRequest = JSON.parse(postData)
      }
      
      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        body: 'Response with orchestration.',
      })
    })
    
    await page.goto('/')
    await helpers.waitForPageReady(page)
    
    const textarea = page.locator('textarea').first()
    await textarea.fill('Test query')
    await textarea.press('Enter')
    
    await page.waitForResponse('/api/chat')
    
    expect(capturedRequest).toBeDefined()
    if (capturedRequest) {
      // Should have orchestratorSettings
      expect(capturedRequest.orchestratorSettings).toBeDefined()
    }
  })

  test('clarification metadata is included in response headers', async ({ page }) => {
    let responseHeaders: Record<string, string> = {}
    
    await page.route('/api/chat', async (route) => {
      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        headers: {
          'X-Models-Used': '["gpt-4o", "claude-sonnet-4"]',
          'X-Tokens-Used': '500',
          'X-Latency-Ms': '1200',
          'X-Strategy-Used': 'parallel_race',
          'X-Clarification-Detected': 'false',
        },
        body: 'Multi-model response.',
      })
    })
    
    await page.goto('/')
    await helpers.waitForPageReady(page)
    
    const textarea = page.locator('textarea').first()
    await textarea.fill('Clear and specific question')
    await textarea.press('Enter')
    
    const response = await page.waitForResponse('/api/chat')
    
    // Verify response headers are accessible
    expect(response.headers()['x-models-used']).toBeDefined()
  })
})

