import { test as base, expect as baseExpect, Page, Route } from '@playwright/test'

/**
 * Extended test fixtures for LLMHive E2E testing.
 * 
 * Usage:
 * import { test, expect, helpers } from './fixtures'
 * 
 * test('my test', async ({ page, mockApi }) => {
 *   await mockApi.mockChatSuccess()
 *   // ... rest of test
 * })
 */

// Standard mock responses
export const MOCK_RESPONSES = {
  chat: {
    success: 'This is a test response from the AI assistant. It demonstrates that the chat system is working correctly.',
    error: 'An error occurred while processing your request.',
  },
  agents: [
    { id: 'gpt-4o', name: 'GPT-4o', provider: 'openai', available: true },
    { id: 'claude-sonnet-4', name: 'Claude Sonnet 4', provider: 'anthropic', available: true },
    { id: 'gemini-2.5-pro', name: 'Gemini 2.5 Pro', provider: 'google', available: true },
    { id: 'grok-2', name: 'Grok 2', provider: 'xai', available: true },
  ],
  settings: {
    orchestratorSettings: {
      reasoningMode: 'standard',
      domainPack: 'default',
      agentMode: 'team',
      promptOptimization: true,
      outputValidation: true,
    },
    criteriaSettings: { accuracy: 70, speed: 70, creativity: 50 },
    preferences: { incognitoMode: false, theme: 'dark' },
  },
  reasoningConfig: {
    mode: 'auto',
    selectedMethods: ['chain_of_thought', 'self_reflection'],
  },
}

// API Mock helpers
interface MockApiHelpers {
  // Chat API mocks
  mockChatSuccess: (response?: string) => Promise<void>
  mockChatError: (status?: number, error?: string) => Promise<void>
  mockChatTimeout: (delayMs?: number) => Promise<void>
  mockChatStreaming: (chunks: string[]) => Promise<void>
  mockChatRetrySuccess: (failCount: number) => Promise<void>
  
  // Agents API mocks
  mockAgentsSuccess: () => Promise<void>
  mockAgentsError: (status?: number) => Promise<void>
  
  // Settings API mocks
  mockSettingsSuccess: () => Promise<void>
  mockSettingsError: () => Promise<void>
  mockSettingsSaveSuccess: () => Promise<void>
  
  // Reasoning config mocks
  mockReasoningConfigSuccess: () => Promise<void>
  
  // Generic helpers
  mockAllApisSuccess: () => Promise<void>
  clearAllMocks: () => Promise<void>
}

// Extended test fixture
export const test = base.extend<{
  mockApi: MockApiHelpers
}>({
  mockApi: async ({ page }, use) => {
    const activeRoutes: Array<() => Promise<void>> = []
    
    const helpers: MockApiHelpers = {
      /**
       * Mock a successful chat API response
       */
      mockChatSuccess: async (response = MOCK_RESPONSES.chat.success) => {
        await page.route('/api/chat', (route) => {
          route.fulfill({
            status: 200,
            contentType: 'text/plain',
            headers: {
              'X-Models-Used': '["gpt-4o"]',
              'X-Tokens-Used': '150',
              'X-Latency-Ms': '450',
            },
            body: response,
          })
        })
      },

      /**
       * Mock a chat API error
       */
      mockChatError: async (status = 500, error = MOCK_RESPONSES.chat.error) => {
        await page.route('/api/chat', (route) => {
          route.fulfill({
            status,
            contentType: 'application/json',
            body: JSON.stringify({ error, message: error }),
          })
        })
      },

      /**
       * Mock a chat API timeout
       */
      mockChatTimeout: async (delayMs = 35000) => {
        await page.route('/api/chat', async (route) => {
          await new Promise(resolve => setTimeout(resolve, delayMs))
          route.abort('timedout')
        })
      },

      /**
       * Mock a streaming chat response
       */
      mockChatStreaming: async (chunks: string[]) => {
        await page.route('/api/chat', async (route) => {
          // Simulate streaming by returning all at once
          // (true streaming would require different approach)
          route.fulfill({
            status: 200,
            contentType: 'text/plain',
            headers: {
              'X-Models-Used': '["gpt-4o"]',
              'X-Tokens-Used': '200',
              'X-Latency-Ms': '800',
            },
            body: chunks.join(''),
          })
        })
      },

      /**
       * Mock chat that fails N times then succeeds (for retry testing)
       */
      mockChatRetrySuccess: async (failCount: number) => {
        let attempts = 0
        await page.route('/api/chat', (route) => {
          attempts++
          if (attempts <= failCount) {
            route.fulfill({
              status: 500,
              contentType: 'application/json',
              body: JSON.stringify({ error: `Attempt ${attempts} failed` }),
            })
          } else {
            route.fulfill({
              status: 200,
              contentType: 'text/plain',
              headers: {
                'X-Models-Used': '["gpt-4o"]',
                'X-Tokens-Used': '100',
                'X-Latency-Ms': '500',
              },
              body: `Success after ${attempts} attempts!`,
            })
          }
        })
      },

      /**
       * Mock a successful agents API response
       */
      mockAgentsSuccess: async () => {
        await page.route('/api/agents', (route) => {
          route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              agents: MOCK_RESPONSES.agents,
            }),
          })
        })
      },

      /**
       * Mock an agents API error
       */
      mockAgentsError: async (status = 500) => {
        await page.route('/api/agents', (route) => {
          route.fulfill({
            status,
            contentType: 'application/json',
            body: JSON.stringify({ error: 'Failed to fetch agents' }),
          })
        })
      },

      /**
       * Mock a successful settings API response
       */
      mockSettingsSuccess: async () => {
        await page.route('/api/settings*', (route) => {
          if (route.request().method() === 'GET') {
            route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify({
                success: true,
                settings: MOCK_RESPONSES.settings,
              }),
            })
          } else {
            route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify({ success: true }),
            })
          }
        })
      },

      /**
       * Mock a settings API error
       */
      mockSettingsError: async () => {
        await page.route('/api/settings*', (route) => {
          route.fulfill({
            status: 500,
            contentType: 'application/json',
            body: JSON.stringify({ error: 'Failed to load settings' }),
          })
        })
      },

      /**
       * Mock settings save success
       */
      mockSettingsSaveSuccess: async () => {
        await page.route('/api/settings*', (route) => {
          if (route.request().method() === 'POST') {
            route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify({ success: true, message: 'Settings saved' }),
            })
          } else {
            route.continue()
          }
        })
      },

      /**
       * Mock reasoning config API
       */
      mockReasoningConfigSuccess: async () => {
        await page.route('/api/reasoning-config*', (route) => {
          if (route.request().method() === 'GET') {
            route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify(MOCK_RESPONSES.reasoningConfig),
            })
          } else {
            route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify({ success: true }),
            })
          }
        })
      },

      /**
       * Mock all APIs with success responses
       */
      mockAllApisSuccess: async () => {
        await helpers.mockChatSuccess()
        await helpers.mockAgentsSuccess()
        await helpers.mockSettingsSuccess()
        await helpers.mockReasoningConfigSuccess()
      },

      /**
       * Clear all route handlers
       */
      clearAllMocks: async () => {
        await page.unrouteAll()
      },
    }

    await use(helpers)
  },
})

export const expect = baseExpect

// Helper functions for common test operations
export const helpers = {
  /**
   * Wait for the page to be fully loaded and interactive
   */
  async waitForPageReady(page: Page) {
    await page.waitForLoadState('domcontentloaded')
    // Wait for React hydration
    await page.waitForFunction(() => {
      return document.readyState === 'complete'
    })
  },

  /**
   * Wait for a specific element to be interactive
   */
  async waitForInteractive(page: Page, selector: string) {
    await page.waitForSelector(selector, { state: 'visible' })
    await page.locator(selector).waitFor({ state: 'attached' })
  },

  /**
   * Send a chat message and wait for response
   */
  async sendChatMessage(page: Page, message: string) {
    const textarea = page.locator('textarea').first()
    await textarea.waitFor({ state: 'visible' })
    await textarea.fill(message)
    await textarea.press('Enter')
  },

  /**
   * Send a chat message and wait for the response to appear
   */
  async sendChatMessageAndWait(page: Page, message: string, expectedResponse?: string) {
    await helpers.sendChatMessage(page, message)
    // Wait for user message to appear
    await page.waitForSelector(`text="${message}"`, { state: 'visible' })
    // Wait for response
    if (expectedResponse) {
      await page.waitForSelector(`text="${expectedResponse.slice(0, 50)}"`, { state: 'visible' })
    } else {
      // Wait for any new content to appear
      await page.waitForTimeout(1000)
    }
  },

  /**
   * Navigate to a route and wait for it to load
   */
  async navigateTo(page: Page, route: 'home' | 'discover' | 'orchestration' | 'settings') {
    const routes: Record<string, string> = {
      home: '/',
      discover: '/discover',
      orchestration: '/orchestration',
      settings: '/settings',
    }
    await page.goto(routes[route])
    await helpers.waitForPageReady(page)
  },

  /**
   * Open a drawer by clicking on a card/button
   */
  async openDrawer(page: Page, buttonName: string) {
    await page.getByRole('button', { name: new RegExp(buttonName, 'i') }).click()
    await page.waitForSelector('[role="dialog"], [data-state="open"]', { state: 'visible', timeout: 5000 })
  },

  /**
   * Close any open drawer
   */
  async closeDrawer(page: Page) {
    await page.keyboard.press('Escape')
    // Wait for drawer animation
    await page.waitForTimeout(300)
  },

  /**
   * Get localStorage value
   */
  async getLocalStorage(page: Page, key: string): Promise<string | null> {
    return page.evaluate((k) => window.localStorage.getItem(k), key)
  },

  /**
   * Set localStorage value
   */
  async setLocalStorage(page: Page, key: string, value: string) {
    await page.evaluate(({ k, v }) => window.localStorage.setItem(k, v), { k: key, v: value })
  },

  /**
   * Clear all localStorage
   */
  async clearLocalStorage(page: Page) {
    await page.evaluate(() => window.localStorage.clear())
  },

  /**
   * Get cookie value
   */
  async getCookie(page: Page, name: string): Promise<string | null> {
    const cookies = await page.context().cookies()
    const cookie = cookies.find(c => c.name === name)
    return cookie?.value ?? null
  },

  /**
   * Set a cookie
   */
  async setCookie(page: Page, name: string, value: string) {
    await page.context().addCookies([{
      name,
      value,
      domain: 'localhost',
      path: '/',
    }])
  },

  /**
   * Clear all cookies
   */
  async clearCookies(page: Page) {
    await page.context().clearCookies()
  },

  /**
   * Capture network request body
   */
  async captureRequestBody(page: Page, urlPattern: string): Promise<any> {
    return new Promise((resolve) => {
      page.route(urlPattern, async (route) => {
        const body = route.request().postData()
        resolve(body ? JSON.parse(body) : null)
        await route.continue()
      })
    })
  },

  /**
   * Wait for a network request to complete
   */
  async waitForRequest(page: Page, urlPattern: string | RegExp) {
    return page.waitForRequest(urlPattern)
  },

  /**
   * Wait for a network response
   */
  async waitForResponse(page: Page, urlPattern: string | RegExp) {
    return page.waitForResponse(urlPattern)
  },

  /**
   * Check if an element is visible without throwing
   */
  async isVisible(page: Page, selector: string): Promise<boolean> {
    try {
      return await page.locator(selector).isVisible()
    } catch {
      return false
    }
  },

  /**
   * Take a screenshot with a descriptive name
   */
  async screenshot(page: Page, name: string) {
    await page.screenshot({ path: `test-results/screenshots/${name}.png`, fullPage: true })
  },
}

// Test data generators
export const testData = {
  /**
   * Generate a random chat message
   */
  chatMessage: () => `Test message ${Date.now()}`,

  /**
   * Generate test settings
   */
  settings: () => ({
    orchestratorSettings: {
      reasoningMode: 'standard',
      domainPack: 'default',
      agentMode: 'team',
      promptOptimization: true,
      outputValidation: true,
    },
    criteriaSettings: {
      accuracy: Math.floor(Math.random() * 100),
      speed: Math.floor(Math.random() * 100),
      creativity: Math.floor(Math.random() * 100),
    },
  }),
}
