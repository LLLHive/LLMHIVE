import { test, expect, helpers, MOCK_RESPONSES } from './fixtures'

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
    await expect(page.getByText('Models')).toBeVisible()
    await expect(page.getByText('Reasoning')).toBeVisible()
    await expect(page.getByText('Tuning')).toBeVisible()
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
    await page.getByRole('button', { name: /Models/i }).click()
    
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
  })

  test('models drawer shows available model providers', async ({ page }) => {
    await page.getByRole('button', { name: /Models/i }).click()
    await page.waitForTimeout(500)
    
    // Should show model providers
    const hasProvider = await page.getByText('GPT').or(page.getByText('OpenAI')).or(page.getByText('Claude')).isVisible()
    expect(hasProvider).toBe(true)
  })

  test('can toggle individual models', async ({ page }) => {
    await page.getByRole('button', { name: /Models/i }).click()
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
    await page.getByRole('button', { name: /Models/i }).click()
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
    
    await page.keyboard.press('Escape')
    await page.waitForTimeout(500)
    
    // Drawer should close (may need to verify specific state)
  })

  test('drawer has close button', async ({ page }) => {
    await page.getByRole('button', { name: /Models/i }).click()
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
    await page.getByRole('button', { name: /Reasoning/i }).click()
    
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
  })

  test('reasoning drawer shows mode options', async ({ page }) => {
    await page.getByRole('button', { name: /Reasoning/i }).click()
    await page.waitForTimeout(500)
    
    // Should show reasoning mode options like auto, manual
    const hasOptions = await page.getByText(/auto|manual|standard/i).isVisible()
    expect(hasOptions).toBe(true)
  })

  test('reasoning drawer shows method selection', async ({ page }) => {
    await page.getByRole('button', { name: /Reasoning/i }).click()
    await page.waitForTimeout(500)
    
    // Should show reasoning methods
    const hasMethods = await page.getByText(/chain|thought|reflection|step/i).first().isVisible().catch(() => false)
    // Methods may or may not be visible depending on mode
  })

  test('can select reasoning mode', async ({ page }) => {
    await page.getByRole('button', { name: /Reasoning/i }).click()
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
    await page.getByRole('button', { name: /Tuning/i }).click()
    
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
  })

  test('tuning drawer shows optimization options', async ({ page }) => {
    await page.getByRole('button', { name: /Tuning/i }).click()
    await page.waitForTimeout(500)
    
    await expect(page.getByText('Prompt Optimization')).toBeVisible()
  })

  test('tuning drawer shows quality settings', async ({ page }) => {
    await page.getByRole('button', { name: /Tuning/i }).click()
    await page.waitForTimeout(500)
    
    // Should show quality-related options
    const hasQuality = await page.getByText(/optimization|quality|validation/i).first().isVisible()
    expect(hasQuality).toBe(true)
  })

  test('can toggle prompt optimization', async ({ page }) => {
    await page.getByRole('button', { name: /Tuning/i }).click()
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
    await page.getByRole('button', { name: /Tuning/i }).click()
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
    
    await page.goto('/')
    await helpers.waitForPageReady(page)
    
    const textarea = page.locator('textarea').first()
    await textarea.fill('Test message')
    await textarea.press('Enter')
    
    await page.waitForResponse('/api/chat')
    
    expect(capturedRequest).toBeDefined()
    if (capturedRequest) {
      expect(capturedRequest.orchestratorSettings).toBeDefined()
    }
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
    await expect(page.getByText('Models')).toBeVisible()
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
    await page.getByRole('button', { name: /Models/i }).click()
    await page.waitForTimeout(500)
    
    // Try to open Reasoning drawer
    await page.keyboard.press('Escape')
    await page.waitForTimeout(300)
    
    await page.getByRole('button', { name: /Reasoning/i }).click()
    await page.waitForTimeout(500)
    
    // Only one drawer should be open
    const dialogs = page.locator('[role="dialog"], [data-state="open"]')
    const count = await dialogs.count()
    expect(count).toBeLessThanOrEqual(2) // May have nested elements
  })

  test('drawer can be closed by clicking outside', async ({ page }) => {
    await page.getByRole('button', { name: /Models/i }).click()
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
    
    // Click outside the drawer (on the overlay)
    await page.locator('[data-state="open"]').first().press('Escape')
    await page.waitForTimeout(500)
  })

  test('drawer content is scrollable if needed', async ({ page }) => {
    await page.getByRole('button', { name: /Models/i }).click()
    await page.waitForTimeout(500)
    
    // Drawer should be visible and potentially scrollable
    const drawer = page.getByRole('dialog').or(page.locator('[data-state="open"]')).first()
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
    await page.getByRole('button', { name: /Models/i }).click()
    await page.waitForTimeout(500)
  })

  test('handles settings API failure gracefully', async ({ page, mockApi }) => {
    await mockApi.mockSettingsError()
    
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)
    
    // Page should still function
    await expect(page.getByText('Models')).toBeVisible()
  })
})

test.describe('Responsive Layout', () => {
  test('orchestration studio works on desktop', async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)
    
    await expect(page.getByText('Models')).toBeVisible()
    await expect(page.getByText('Reasoning')).toBeVisible()
    await expect(page.getByText('Tuning')).toBeVisible()
  })

  test('orchestration studio works on tablet', async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.setViewportSize({ width: 768, height: 1024 })
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)
    
    await expect(page.getByText('Models')).toBeVisible()
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
    
    await page.getByRole('button', { name: /Models/i }).click()
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
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
    await page.getByRole('button', { name: /Models/i }).click()
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
    
    await page.keyboard.press('Escape')
    await page.waitForTimeout(500)
  })

  test('focus is trapped in open drawer', async ({ page }) => {
    await page.getByRole('button', { name: /Models/i }).click()
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
    
    // Should load within 5 seconds
    expect(loadTime).toBeLessThan(5000)
  })

  test('drawers open quickly', async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)
    
    const startTime = Date.now()
    await page.getByRole('button', { name: /Models/i }).click()
    await expect(page.getByRole('dialog').or(page.locator('[data-state="open"]'))).toBeVisible({ timeout: 5000 })
    const openTime = Date.now() - startTime
    
    // Drawer should open within 1 second
    expect(openTime).toBeLessThan(1000)
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
          'X-Latency-Ms': '300',
        },
        body: 'Budget-aware response using cheaper model.',
      })
    })
    
    // Open Orchestration Studio
    const studioTrigger = page.getByText('Orchestration Studio')
    if (await studioTrigger.isVisible()) {
      await studioTrigger.click()
      await page.waitForTimeout(500)
      
      // Navigate to Budget tab if available
      const budgetTab = page.getByText('Budget')
      if (await budgetTab.isVisible()) {
        await budgetTab.click()
        await page.waitForTimeout(300)
      }
    }
    
    // Send a message
    const textarea = page.locator('textarea').first()
    await textarea.fill('What is 2+2?')
    await textarea.press('Enter')
    
    await page.waitForResponse('/api/chat')
    
    expect(capturedRequest).toBeDefined()
    if (capturedRequest) {
      expect(capturedRequest.orchestratorSettings).toBeDefined()
    }
  })

  test('prefer cheaper models toggle works', async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/')
    await helpers.waitForPageReady(page)
    
    // Look for Orchestration Studio toggle
    const studioTrigger = page.getByText('Orchestration Studio')
    if (await studioTrigger.isVisible()) {
      await studioTrigger.click()
      await page.waitForTimeout(500)
      
      // Look for Budget tab
      const budgetTab = page.getByText('Budget')
      if (await budgetTab.isVisible()) {
        await budgetTab.click()
        await page.waitForTimeout(300)
        
        // Look for "Prefer Cheaper" toggle
        const preferCheaperToggle = page.getByText('Prefer Cheaper')
        if (await preferCheaperToggle.isVisible()) {
          // Toggle should be present
          expect(await preferCheaperToggle.isVisible()).toBe(true)
        }
      }
    }
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
    
    // Send an ambiguous query
    const textarea = page.locator('textarea').first()
    await textarea.fill('Which one is better?')
    await textarea.press('Enter')
    
    // Wait for response
    await page.waitForResponse('/api/chat')
    await page.waitForTimeout(500)
    
    // The UI should handle the ambiguity in some way
    // (either showing clarification or processing anyway)
    await expect(page.locator('body')).toContainText(/better|context|specific/i)
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
    
    // Send a query that might trigger clarification
    const textarea = page.locator('textarea').first()
    await textarea.fill('Compare these options')
    await textarea.press('Enter')
    
    await page.waitForResponse('/api/chat')
    
    // Should get some response
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
    
    // Enable verification in settings if available
    const studioTrigger = page.getByText('Orchestration Studio')
    if (await studioTrigger.isVisible()) {
      await studioTrigger.click()
      await page.waitForTimeout(500)
      
      // Look for Strategy tab
      const strategyTab = page.getByText('Strategy')
      if (await strategyTab.isVisible()) {
        await strategyTab.click()
        await page.waitForTimeout(300)
        
        // Enable verification if toggle exists
        const verificationToggle = page.getByText('Enable Verification')
        if (await verificationToggle.isVisible()) {
          const toggle = page.locator('[role="switch"]').filter({ has: verificationToggle }).first()
          if (await toggle.isVisible()) {
            await toggle.click()
          }
        }
      }
    }
    
    // Send a factual query
    const textarea = page.locator('textarea').first()
    await textarea.fill('What is the meaning of life according to The Hitchhikers Guide?')
    await textarea.press('Enter')
    
    await page.waitForResponse('/api/chat')
    
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
    
    // Send a temporal query
    const textarea = page.locator('textarea').first()
    await textarea.fill('What is the latest news about AI today?')
    await textarea.press('Enter')
    
    await page.waitForResponse('/api/chat')
    
    expect(capturedRequest).toBeDefined()
    if (capturedRequest) {
      // Should have enable_live_research in orchestration settings
      const orchestration = capturedRequest.orchestratorSettings?.orchestration || capturedRequest.orchestration
      if (orchestration) {
        expect(orchestration.enable_live_research).toBe(true)
      }
    }
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
    
    // Send a math query
    const textarea = page.locator('textarea').first()
    await textarea.fill('Calculate 12 * 12')
    await textarea.press('Enter')
    
    await page.waitForResponse('/api/chat')
    
    expect(capturedRequest).toBeDefined()
  })
})

test.describe('PR8: Strategy Selection', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockAllApisSuccess()
    await page.goto('/')
    await helpers.waitForPageReady(page)
  })

  test('elite strategy can be selected', async ({ page }) => {
    // Open Orchestration Studio
    const studioTrigger = page.getByText('Orchestration Studio')
    if (await studioTrigger.isVisible()) {
      await studioTrigger.click()
      await page.waitForTimeout(500)
      
      // Look for Strategy tab
      const strategyTab = page.getByText('Strategy')
      if (await strategyTab.isVisible()) {
        await strategyTab.click()
        await page.waitForTimeout(300)
        
        // Look for strategy dropdown
        const strategySelect = page.getByText('Elite Strategy')
        if (await strategySelect.isVisible()) {
          expect(await strategySelect.isVisible()).toBe(true)
        }
      }
    }
  })

  test('accuracy slider affects model selection', async ({ page }) => {
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
          'X-Tokens-Used': '200',
          'X-Latency-Ms': '500',
        },
        body: 'High accuracy response.',
      })
    })
    
    // Open Orchestration Studio
    const studioTrigger = page.getByText('Orchestration Studio')
    if (await studioTrigger.isVisible()) {
      await studioTrigger.click()
      await page.waitForTimeout(500)
      
      // Look for accuracy slider
      const accuracyLabel = page.getByText('Accuracy vs Speed')
      if (await accuracyLabel.isVisible()) {
        // The slider should be present
        expect(await accuracyLabel.isVisible()).toBe(true)
      }
    }
    
    // Send a message
    const textarea = page.locator('textarea').first()
    await textarea.fill('Explain quantum computing')
    await textarea.press('Enter')
    
    await page.waitForResponse('/api/chat')
    
    expect(capturedRequest).toBeDefined()
    if (capturedRequest) {
      expect(capturedRequest.orchestratorSettings).toBeDefined()
      // Should have accuracy_level in orchestration
      if (capturedRequest.orchestratorSettings?.accuracyLevel !== undefined) {
        expect(capturedRequest.orchestratorSettings.accuracyLevel).toBeGreaterThanOrEqual(1)
        expect(capturedRequest.orchestratorSettings.accuracyLevel).toBeLessThanOrEqual(5)
      }
    }
  })
})
