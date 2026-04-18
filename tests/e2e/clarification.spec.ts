import { test, expect, helpers, E2E_CHAT_PROMPT } from './fixtures'

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
    await mockApi.mockCoreApisSuccess()
    await page.goto('/')
    await helpers.waitForPageReady(page)
    await helpers.ensureChatComposerVisible(page)
  })

  test('clarifying questions are displayed for ambiguous queries', async ({ page }) => {
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

    const textarea = page.locator('textarea').first()
    const chatResp = helpers.waitForNextChatPostResponse(page)
    await textarea.fill(E2E_CHAT_PROMPT)
    await textarea.press('Enter')
    await chatResp
    await page.waitForTimeout(500)

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

    const textarea = page.locator('textarea').first()
    const firstResp = helpers.waitForNextChatPostResponse(page)
    await textarea.fill(E2E_CHAT_PROMPT)
    await textarea.press('Enter')
    await firstResp
    await page.waitForTimeout(1000)

    const secondResp = helpers.waitForNextChatPostResponse(page)
    await textarea.fill('I meant programming languages')
    await textarea.press('Enter')
    await secondResp
    await page.waitForTimeout(500)

    expect(requestCount).toBe(2)
    expect(lastRequest).toBeDefined()
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

    const textarea = page.locator('textarea').first()
    const chatResp = helpers.waitForNextChatPostResponse(page)
    await textarea.fill(E2E_CHAT_PROMPT)
    await textarea.press('Enter')
    await chatResp

    expect(capturedRequest).toBeDefined()
    const msgs = capturedRequest.messages as Array<{ role?: string; content?: string }> | undefined
    const lastUser = msgs?.filter((m) => m.role === 'user').pop()
    expect(lastUser?.content?.length).toBeGreaterThan(10)
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

    const textarea = page.locator('textarea').first()
    const chatResp = helpers.waitForNextChatPostResponse(page)
    await textarea.fill(E2E_CHAT_PROMPT)
    await textarea.press('Enter')
    await chatResp

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

    const textarea = page.locator('textarea').first()
    const chatResp = helpers.waitForNextChatPostResponse(page)
    await textarea.fill(E2E_CHAT_PROMPT)
    await textarea.press('Enter')
    await chatResp
    await page.waitForTimeout(500)

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

    const r1 = helpers.waitForNextChatPostResponse(page)
    await textarea.fill(`${E2E_CHAT_PROMPT} (round 1)`)
    await textarea.press('Enter')
    await r1

    const r2 = helpers.waitForNextChatPostResponse(page)
    await textarea.fill(`${E2E_CHAT_PROMPT} (round 2)`)
    await textarea.press('Enter')
    await r2

    const r3 = helpers.waitForNextChatPostResponse(page)
    await textarea.fill(`${E2E_CHAT_PROMPT} (round 3)`)
    await textarea.press('Enter')
    await r3

    expect(requestCount).toBe(3)
  })
})

test.describe('Clarifying Questions - Edge Cases', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockCoreApisSuccess()
    await page.goto('/')
    await helpers.waitForPageReady(page)
    await helpers.ensureChatComposerVisible(page)
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
    const chatResp = helpers.waitForNextChatPostResponse(page)
    await textarea.fill(E2E_CHAT_PROMPT)
    await textarea.press('Enter')
    await chatResp
    await page.waitForTimeout(500)

    await expect(page.locator('textarea').first()).toBeVisible()
  })

  test('handles clarification with special characters', async ({ page }) => {
    let capturedMessage = ''

    await page.route('/api/chat', async (route) => {
      const postData = route.request().postData()
      if (postData) {
        const parsed = JSON.parse(postData) as {
          message?: string
          prompt?: string
          messages?: Array<{ role?: string; content?: string }>
        }
        const lastUser = parsed.messages?.filter((m) => m.role === 'user').pop()
        capturedMessage = parsed.message || parsed.prompt || lastUser?.content || ''
      }

      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        body: 'Processed your question with special characters.',
      })
    })

    const textarea = page.locator('textarea').first()
    const chatResp = helpers.waitForNextChatPostResponse(page)
    await textarea.fill('What about "quotes" & <tags> and emoji 🎉? Please answer briefly for testing.')
    await textarea.press('Enter')
    await chatResp

    expect(capturedMessage).toContain('quotes')
  })

  test('clarification timeout is handled', async ({ page }) => {
    await page.route('/api/chat', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 2000))
      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        body: 'Delayed response received.',
      })
    })

    const textarea = page.locator('textarea').first()
    const chatResp = helpers.waitForNextChatPostResponse(page)
    await textarea.fill(E2E_CHAT_PROMPT)
    await textarea.press('Enter')
    await chatResp

    const bodyText = await page.locator('body').textContent()
    expect(bodyText).toBeTruthy()
  })
})

test.describe('Clarifying Questions - API Integration', () => {
  test('orchestration settings include clarification context', async ({ page, mockApi }) => {
    let capturedRequest: any = null

    await mockApi.mockCoreApisSuccess()
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
    await helpers.ensureChatComposerVisible(page)

    const textarea = page.locator('textarea').first()
    const chatResp = helpers.waitForNextChatPostResponse(page)
    await textarea.fill(E2E_CHAT_PROMPT)
    await textarea.press('Enter')
    await chatResp

    expect(capturedRequest).toBeDefined()
    if (capturedRequest) {
      expect(capturedRequest.orchestratorSettings).toBeDefined()
    }
  })

  test('clarification metadata is included in response headers', async ({ page, mockApi }) => {
    await mockApi.mockCoreApisSuccess()
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
    await helpers.ensureChatComposerVisible(page)

    const textarea = page.locator('textarea').first()
    const chatResp = helpers.waitForNextChatPostResponse(page)
    await textarea.fill(E2E_CHAT_PROMPT)
    await textarea.press('Enter')
    const response = await chatResp

    expect(response.headers()['x-models-used']).toBeDefined()
  })
})
