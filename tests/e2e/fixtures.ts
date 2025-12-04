import { test as base, expect as baseExpect, Page } from '@playwright/test'

/**
 * Extended test fixtures for LLMHive E2E testing.
 * 
 * Usage:
 * import { test, expect } from './fixtures'
 * 
 * test('my test', async ({ page, mockApi }) => {
 *   await mockApi.mockChatSuccess()
 *   // ... rest of test
 * })
 */

// API Mock helpers
interface MockApiHelpers {
  mockChatSuccess: (response?: string) => Promise<void>
  mockChatError: (status?: number, error?: string) => Promise<void>
  mockChatTimeout: (delayMs?: number) => Promise<void>
  mockAgentsSuccess: () => Promise<void>
  mockSettingsSuccess: () => Promise<void>
}

// Extended test fixture
export const test = base.extend<{
  mockApi: MockApiHelpers
}>({
  mockApi: async ({ page }, use) => {
    const helpers: MockApiHelpers = {
      /**
       * Mock a successful chat API response
       */
      mockChatSuccess: async (response = 'This is a test response from the AI assistant.') => {
        await page.route('/api/chat', (route) => {
          route.fulfill({
            status: 200,
            contentType: 'text/plain',
            headers: {
              'X-Models-Used': '["gpt-4o"]',
              'X-Tokens-Used': '100',
              'X-Latency-Ms': '500',
            },
            body: response,
          })
        })
      },

      /**
       * Mock a chat API error
       */
      mockChatError: async (status = 500, error = 'Internal server error') => {
        await page.route('/api/chat', (route) => {
          route.fulfill({
            status,
            contentType: 'application/json',
            body: JSON.stringify({ error }),
          })
        })
      },

      /**
       * Mock a chat API timeout
       */
      mockChatTimeout: async (delayMs = 10000) => {
        await page.route('/api/chat', async (route) => {
          await new Promise(resolve => setTimeout(resolve, delayMs))
          route.abort('timedout')
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
              agents: [
                { id: 'gpt-4o', name: 'GPT-4o', provider: 'openai', available: true },
                { id: 'claude-sonnet-4', name: 'Claude Sonnet 4', provider: 'anthropic', available: true },
                { id: 'gemini-2.5-pro', name: 'Gemini 2.5 Pro', provider: 'google', available: true },
              ],
            }),
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
    await page.waitForLoadState('networkidle')
    await page.waitForSelector('img[alt="LLMHive"]', { state: 'visible', timeout: 10000 })
  },

  /**
   * Send a chat message and wait for response
   */
  async sendChatMessage(page: Page, message: string) {
    const textarea = page.locator('textarea[placeholder*="Ask"], textarea[placeholder*="Message"]').first()
    await textarea.fill(message)
    await textarea.press('Enter')
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
    await page.waitForLoadState('networkidle')
  },

  /**
   * Open a drawer by clicking on a card
   */
  async openDrawer(page: Page, cardText: string) {
    await page.click(`button:has-text("${cardText}")`)
    await page.waitForSelector('[role="dialog"], [data-state="open"]', { state: 'visible' })
  },

  /**
   * Close any open drawer
   */
  async closeDrawer(page: Page) {
    await page.keyboard.press('Escape')
    await page.waitForSelector('[role="dialog"], [data-state="open"]', { state: 'hidden', timeout: 2000 }).catch(() => {})
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
}

// Custom matchers (optional)
export const customMatchers = {
  /**
   * Check if element has bronze color styling
   */
  async toHaveBronzeStyle(element: any) {
    const classes = await element.getAttribute('class')
    const hasBronze = classes?.includes('bronze') || classes?.includes('var(--bronze)')
    return {
      pass: hasBronze,
      message: () => `Expected element to have bronze styling`,
    }
  },
}
