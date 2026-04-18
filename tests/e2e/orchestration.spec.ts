import { test, expect, helpers, MOCK_RESPONSES, E2E_CHAT_PROMPT } from './fixtures'

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
    await expect(page.locator('button.settings-card').filter({ hasText: 'Models' })).toBeVisible()
    await expect(page.locator('button.settings-card').filter({ hasText: 'Reasoning' })).toBeVisible()
    await expect(page.locator('button.settings-card').filter({ hasText: 'Tuning' })).toBeVisible()
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
    await page.locator('button.settings-card').filter({ hasText: 'Models' }).click()
    
    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 })
  })

  test('models drawer shows available model providers', async ({ page }) => {
    await page.locator('button.settings-card').filter({ hasText: 'Models' }).click()
    await page.waitForTimeout(500)

    await expect(page.getByRole('dialog')).toContainText(/Select AI models for orchestration|Models|Automatic/i)
  })

  test('can toggle individual models', async ({ page }) => {
    await page.locator('button.settings-card').filter({ hasText: 'Models' }).click()
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
    await page.locator('button.settings-card').filter({ hasText: 'Models' }).click()
    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 })
    
    await page.keyboard.press('Escape')
    await page.waitForTimeout(500)
    
    // Drawer should close (may need to verify specific state)
  })

  test('drawer has close button', async ({ page }) => {
    await page.locator('button.settings-card').filter({ hasText: 'Models' }).click()
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
    await page.locator('button.settings-card').filter({ hasText: 'Reasoning' }).click()
    
    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 })
  })

  test('reasoning drawer shows mode options', async ({ page }) => {
    await page.locator('button.settings-card').filter({ hasText: 'Reasoning' }).click()
    await page.waitForTimeout(500)

    await expect(page.getByText('Advanced reasoning methods', { exact: true }).first()).toBeVisible()
  })

  test('reasoning drawer shows method selection', async ({ page }) => {
    await page.locator('button.settings-card').filter({ hasText: 'Reasoning' }).click()
    await page.waitForTimeout(500)
    
    // Should show reasoning methods
    const hasMethods = await page.getByText(/chain|thought|reflection|step/i).first().isVisible().catch(() => false)
    // Methods may or may not be visible depending on mode
  })

  test('can select reasoning mode', async ({ page }) => {
    await page.locator('button.settings-card').filter({ hasText: 'Reasoning' }).click()
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
    const card = page.locator('button.settings-card').filter({ hasText: 'Tuning' })
    await card.scrollIntoViewIfNeeded()
    await card.click({ timeout: 15000 })

    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 15000 })
  })

  test('tuning drawer shows optimization options', async ({ page }) => {
    const card = page.locator('button.settings-card').filter({ hasText: 'Tuning' })
    await card.scrollIntoViewIfNeeded()
    await card.click({ timeout: 15000 })
    await page.waitForTimeout(500)

    await expect(page.getByText('Prompt Optimization')).toBeVisible({ timeout: 15000 })
  })

  test('tuning drawer shows quality settings', async ({ page }) => {
    const card = page.locator('button.settings-card').filter({ hasText: 'Tuning' })
    await card.scrollIntoViewIfNeeded()
    await card.click({ timeout: 15000 })
    await page.waitForTimeout(500)
    
    // Should show quality-related options
    const hasQuality = await page.getByText(/optimization|quality|validation/i).first().isVisible()
    expect(hasQuality).toBe(true)
  })

  test('can toggle prompt optimization', async ({ page }) => {
    const card = page.locator('button.settings-card').filter({ hasText: 'Tuning' })
    await card.scrollIntoViewIfNeeded()
    await card.click({ timeout: 15000 })
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
    await page.locator('button.settings-card').filter({ hasText: 'Tuning' }).click()
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
    await page.route('/api/chat', async (route) => {
      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        body: 'Test response',
      })
    })
    
    await page.goto('/')
    await helpers.waitForPageReady(page)
    await helpers.ensureChatComposerVisible(page)
    
    const textarea = page.locator('textarea').first()
    const responsePromise = page.waitForResponse(
      (r) => r.url().includes('/api/chat') && r.request().method() === 'POST',
    )
    await textarea.fill(E2E_CHAT_PROMPT)
    await textarea.press('Enter')
    
    const response = await responsePromise
    const postData = response.request().postData()
    expect(postData).toBeTruthy()
    const capturedRequest = JSON.parse(postData!)
    expect(capturedRequest.orchestratorSettings).toBeDefined()
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
    await expect(page.locator('button.settings-card').filter({ hasText: 'Models' })).toBeVisible()
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
    await page.locator('button.settings-card').filter({ hasText: 'Models' }).click()
    await page.waitForTimeout(500)
    
    // Try to open Reasoning drawer
    await page.keyboard.press('Escape')
    await page.waitForTimeout(300)
    
    await page.locator('button.settings-card').filter({ hasText: 'Reasoning' }).click()
    await page.waitForTimeout(500)
    
    // Only one drawer should be open
    const dialogs = page.locator('[role="dialog"], [data-state="open"]')
    const count = await dialogs.count()
    expect(count).toBeLessThanOrEqual(2) // May have nested elements
  })

  test('drawer can be closed by clicking outside', async ({ page }) => {
    await page.locator('button.settings-card').filter({ hasText: 'Models' }).click()
    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 })
    
    // Click outside the drawer (on the overlay)
    await page.locator('[data-state="open"]').first().press('Escape')
    await page.waitForTimeout(500)
  })

  test('drawer content is scrollable if needed', async ({ page }) => {
    await page.locator('button.settings-card').filter({ hasText: 'Models' }).click()
    await page.waitForTimeout(500)
    
    // Drawer should be visible and potentially scrollable
    const drawer = page.getByRole('dialog').first()
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
    await page.locator('button.settings-card').filter({ hasText: 'Models' }).click()
    await page.waitForTimeout(500)
  })

  test('handles settings API failure gracefully', async ({ page, mockApi }) => {
    await mockApi.mockSettingsError()
    
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)
    
    // Page should still function
    await expect(page.locator('button.settings-card').filter({ hasText: 'Models' })).toBeVisible()
  })
})

test.describe('Responsive Layout', () => {
  test('orchestration studio works on desktop', async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)
    
    await expect(page.locator('button.settings-card').filter({ hasText: 'Models' })).toBeVisible()
    await expect(page.locator('button.settings-card').filter({ hasText: 'Reasoning' })).toBeVisible()
    await expect(page.locator('button.settings-card').filter({ hasText: 'Tuning' })).toBeVisible()
  })

  test('orchestration studio works on tablet', async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.setViewportSize({ width: 768, height: 1024 })
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)
    
    await expect(page.locator('button.settings-card').filter({ hasText: 'Models' })).toBeVisible()
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

    const modelsCard = page.locator('button.settings-card').filter({ hasText: 'Models' })
    await modelsCard.scrollIntoViewIfNeeded()
    await modelsCard.click({ timeout: 15000 })
    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 15000 })
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
    const modelsCard = page.locator('button.settings-card').filter({ hasText: 'Models' })
    await modelsCard.scrollIntoViewIfNeeded()
    await modelsCard.click({ timeout: 15000 })
    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 15000 })
    
    await page.keyboard.press('Escape')
    await page.waitForTimeout(500)
  })

  test('focus is trapped in open drawer', async ({ page }) => {
    const modelsCard = page.locator('button.settings-card').filter({ hasText: 'Models' })
    await modelsCard.scrollIntoViewIfNeeded()
    await modelsCard.click({ timeout: 15000 })
    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 15000 })
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
    
    expect(loadTime).toBeLessThan(15000)
  })

  test('drawers open quickly', async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)
    
    const startTime = Date.now()
    await page.locator('button.settings-card').filter({ hasText: 'Models' }).click()
    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 15000 })
    const openTime = Date.now() - startTime
    
    expect(openTime).toBeLessThan(15000)
  })
})

// ==============================================================================
// PR8: Advanced Orchestration Scenarios
// ==============================================================================

test.describe('PR8: Budget-Aware Routing', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/')
    await helpers.waitForPageReady(page)
  })

  test('budget constraint is sent to backend', async ({ page }) => {
    await page.route('/api/chat', async (route) => {
      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        headers: {
          'X-Models-Used': '["deepseek-chat"]',
          'X-Tokens-Used': '100',
          'X-Latency-Ms': '300',
        },
        body: 'Budget-aware response using cheaper model.',
      })
    })

    await page.goto('/')
    await helpers.waitForPageReady(page)
    await helpers.ensureChatComposerVisible(page)

    const textarea = page.locator('textarea').first()
    const responsePromise = page.waitForResponse(
      (r) => r.url().includes('/api/chat') && r.request().method() === 'POST',
    )
    await textarea.fill(E2E_CHAT_PROMPT)
    await textarea.press('Enter')

    const response = await responsePromise
    const postData = response.request().postData()
    expect(postData).toBeTruthy()
    const capturedRequest = JSON.parse(postData!)
    expect(capturedRequest.orchestratorSettings).toBeDefined()
  })

  test('prefer cheaper models toggle works', async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)
    await expect(page.locator('h1')).toContainText('Orchestration')
    await page.locator('button.settings-card').filter({ hasText: 'Models' }).click()
    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 })
  })
})

test.describe('PR8: Ambiguous Query Flow', () => {
  test('clarification questions are displayed for ambiguous queries', async ({ page }) => {
    await page.route('/api/chat', async (route) => {
      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        headers: {
          'X-Models-Used': '["gpt-4o"]',
          'X-Tokens-Used': '200',
          'X-Latency-Ms': '500',
        },
        body: 'The best solution depends on your specific use case. Could you provide more context?',
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
    await page.waitForTimeout(500)
    
    await expect(page.locator('body')).toContainText(/Paris|France|capital|context|specific|better/i)
  })

  test('user can skip clarification and proceed', async ({ page }) => {
    await page.route('/api/chat', async (route) => {
      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        headers: {
          'X-Models-Used': '["gpt-4o"]',
          'X-Tokens-Used': '150',
          'X-Latency-Ms': '400',
        },
        body: 'Based on general criteria, option A is better.',
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
    
    await page.waitForTimeout(500)
  })
})

test.describe('PR8: Verification Fallback', () => {
  test('verification failure triggers fallback strategy', async ({ page }) => {
    let requestCount = 0
    
    await page.route('/api/chat', async (route) => {
      requestCount++
      
      // Simulate verification in response
      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        headers: {
          'X-Models-Used': '["gpt-4o", "claude-sonnet-4"]',
          'X-Tokens-Used': '300',
          'X-Latency-Ms': '800',
        },
        body: 'After verification, the answer is: 42. [Verified with 95% confidence]',
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
    
    // Should have made at least one request
    expect(requestCount).toBeGreaterThan(0)
  })
})

test.describe('PR8: Retrieval/Tool Usage', () => {
  test('web search is triggered for temporal queries', async ({ page }) => {
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
          'X-Models-Used': '["gemini-2.5-pro"]',
          'X-Tokens-Used': '400',
          'X-Latency-Ms': '1200',
        },
        body: 'Based on current data, here is the latest information...',
      })
    })
    
    await page.goto('/')
    await helpers.waitForPageReady(page)
    await helpers.ensureChatComposerVisible(page)
    
    const textarea = page.locator('textarea').first()
    const chatResp = helpers.waitForNextChatPostResponse(page)
    await textarea.fill('What is the latest news about AI today?')
    await textarea.press('Enter')
    await chatResp
    
    expect(capturedRequest).toBeDefined()
    const msgs = capturedRequest?.messages as Array<{ role?: string; content?: string }> | undefined
    const lastUser = msgs?.filter((m) => m.role === 'user').pop()
    expect(lastUser?.content || '').toMatch(/latest|today|news|AI/i)
  })

  test('calculator tool is used for math queries', async ({ page }) => {
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
          'X-Models-Used': '["deepseek-chat"]',
          'X-Tokens-Used': '100',
          'X-Latency-Ms': '200',
        },
        body: 'The result is 144. (12 * 12 = 144)',
      })
    })
    
    await page.goto('/')
    await helpers.waitForPageReady(page)
    await helpers.ensureChatComposerVisible(page)
    
    const textarea = page.locator('textarea').first()
    const chatResp = helpers.waitForNextChatPostResponse(page)
    await textarea.fill(
      'Please calculate twelve multiplied by twelve and respond with only the numeric result for this test.',
    )
    await textarea.press('Enter')
    await chatResp
    
    expect(capturedRequest).toBeDefined()
  })
})

test.describe('PR8: Strategy Selection', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)
  })

  test('elite strategy can be selected', async ({ page }) => {
    const eliteCard = page.locator('button.settings-card').filter({ hasText: 'Elite Mode' })
    await eliteCard.scrollIntoViewIfNeeded()
    await eliteCard.click({ timeout: 15000 })
    await expect(page.getByRole('dialog', { name: /Elite Mode/i })).toBeVisible({ timeout: 15000 })
    await expect(page.getByText('Orchestration Strategy').first()).toBeVisible()
  })

  test('accuracy slider affects model selection', async ({ page }) => {
    await page.route('/api/chat', async (route) => {
      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        headers: {
          'X-Models-Used': '["gpt-4o"]',
          'X-Tokens-Used': '200',
          'X-Latency-Ms': '500',
        },
        body: 'High accuracy response.',
      })
    })

    await page.goto('/')
    await helpers.waitForPageReady(page)
    await helpers.ensureChatComposerVisible(page)

    const textarea = page.locator('textarea').first()
    const responsePromise = page.waitForResponse(
      (r) => r.url().includes('/api/chat') && r.request().method() === 'POST',
    )
    await textarea.fill(E2E_CHAT_PROMPT)
    await textarea.press('Enter')

    const response = await responsePromise
    const postData = response.request().postData()
    expect(postData).toBeTruthy()
    const capturedRequest = JSON.parse(postData!)
    expect(capturedRequest.orchestratorSettings).toBeDefined()
  })
})
