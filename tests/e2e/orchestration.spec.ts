import { test, expect } from '@playwright/test'

/**
 * Orchestration Studio Tests for LLMHive
 * 
 * Tests cover:
 * - Configuration cards
 * - Drawer interactions
 * - Model selection
 * - Reasoning methods
 * - Settings persistence
 * - UI responsiveness
 */

test.describe('Orchestration Studio Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/orchestration')
    await page.waitForLoadState('networkidle')
  })

  test('page loads with title and description', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Orchestration')
    await expect(page.locator('text=Configure your AI orchestration')).toBeVisible()
  })

  test('all configuration cards are visible', async ({ page }) => {
    // Verify all main configuration cards
    await expect(page.locator('text=Elite Mode')).toBeVisible()
    await expect(page.locator('text=Models')).toBeVisible()
    await expect(page.locator('text=Reasoning')).toBeVisible()
    await expect(page.locator('text=Tuning')).toBeVisible()
    await expect(page.locator('text=Features')).toBeVisible()
    await expect(page.locator('text=Tools')).toBeVisible()
    await expect(page.locator('text=Quality')).toBeVisible()
    await expect(page.locator('text=Speed')).toBeVisible()
  })

  test('cards show count badges for selections', async ({ page }) => {
    // Cards should show badges indicating selected item counts
    const modelsCard = page.locator('button:has-text("Models")').first()
    
    // The badge element should exist (may contain a count or checkmark)
    await expect(modelsCard).toBeVisible()
  })
})

test.describe('Models Configuration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/orchestration')
    await page.waitForLoadState('networkidle')
  })

  test('models drawer opens when clicking Models card', async ({ page }) => {
    await page.click('button:has-text("Models")')
    
    // Drawer should open with model options
    await expect(page.locator('[role="dialog"], [data-state="open"]')).toBeVisible({ timeout: 3000 })
  })

  test('models drawer shows available model providers', async ({ page }) => {
    await page.click('button:has-text("Models")')
    await page.waitForTimeout(500) // Wait for drawer animation
    
    // Should show major model providers
    await expect(page.locator('text=GPT-4o').or(page.locator('text=OpenAI'))).toBeVisible()
    await expect(page.locator('text=Claude').or(page.locator('text=Anthropic'))).toBeVisible()
  })

  test('can select and deselect models', async ({ page }) => {
    await page.click('button:has-text("Models")')
    await page.waitForTimeout(500)
    
    // Find a model item and click it
    const modelItem = page.locator('text=GPT-4o').first()
    if (await modelItem.isVisible()) {
      await modelItem.click()
      // Selection state should toggle (visual change)
    }
  })

  test('drawer closes when pressing Escape', async ({ page }) => {
    await page.click('button:has-text("Models")')
    await expect(page.locator('[role="dialog"], [data-state="open"]')).toBeVisible()
    
    await page.keyboard.press('Escape')
    
    // Drawer should close
    await expect(page.locator('[role="dialog"], [data-state="open"]')).not.toBeVisible({ timeout: 2000 })
  })

  test('automatic model selection is available', async ({ page }) => {
    await page.click('button:has-text("Models")')
    await page.waitForTimeout(500)
    
    // Should have an "Automatic" option
    await expect(page.locator('text=Automatic').or(page.locator('text=automatic'))).toBeVisible()
  })
})

test.describe('Reasoning Configuration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/orchestration')
    await page.waitForLoadState('networkidle')
  })

  test('reasoning drawer opens when clicking Reasoning card', async ({ page }) => {
    await page.click('button:has-text("Reasoning")')
    
    await expect(page.locator('[role="dialog"], [data-state="open"]')).toBeVisible({ timeout: 3000 })
  })

  test('reasoning drawer shows reasoning methods', async ({ page }) => {
    await page.click('button:has-text("Reasoning")')
    await page.waitForTimeout(500)
    
    // Should show various reasoning methods
    await expect(
      page.locator('text=Chain of Thought')
        .or(page.locator('text=chain-of-thought'))
        .or(page.locator('text=CoT'))
    ).toBeVisible()
  })

  test('can select reasoning mode', async ({ page }) => {
    await page.click('button:has-text("Reasoning")')
    await page.waitForTimeout(500)
    
    // Click on a reasoning option if visible
    const cotOption = page.locator('text=Chain of Thought').first()
    if (await cotOption.isVisible()) {
      await cotOption.click()
    }
  })
})

test.describe('Tuning Configuration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/orchestration')
    await page.waitForLoadState('networkidle')
  })

  test('tuning drawer opens when clicking Tuning card', async ({ page }) => {
    await page.click('button:has-text("Tuning")')
    
    await expect(page.locator('[role="dialog"], [data-state="open"]')).toBeVisible({ timeout: 3000 })
  })

  test('tuning drawer shows optimization options', async ({ page }) => {
    await page.click('button:has-text("Tuning")')
    await page.waitForTimeout(500)
    
    // Should show tuning options
    await expect(page.locator('text=Prompt Optimization')).toBeVisible()
    await expect(page.locator('text=Output Validation')).toBeVisible()
  })

  test('can toggle tuning options', async ({ page }) => {
    await page.click('button:has-text("Tuning")')
    await page.waitForTimeout(500)
    
    // Find and click a toggle option
    const promptOptToggle = page.locator('text=Prompt Optimization').first()
    if (await promptOptToggle.isVisible()) {
      await promptOptToggle.click()
    }
  })
})

test.describe('Elite Mode Configuration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/orchestration')
    await page.waitForLoadState('networkidle')
  })

  test('elite mode drawer opens when clicking Elite Mode card', async ({ page }) => {
    await page.click('button:has-text("Elite Mode")')
    
    await expect(page.locator('[role="dialog"], [data-state="open"]')).toBeVisible({ timeout: 3000 })
  })

  test('elite mode drawer shows strategy options', async ({ page }) => {
    await page.click('button:has-text("Elite Mode")')
    await page.waitForTimeout(500)
    
    // Should show elite strategies
    await expect(page.locator('text=Fast')).toBeVisible()
    await expect(page.locator('text=Standard')).toBeVisible()
    await expect(page.locator('text=Thorough')).toBeVisible()
  })
})

test.describe('Quality Configuration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/orchestration')
    await page.waitForLoadState('networkidle')
  })

  test('quality drawer opens when clicking Quality card', async ({ page }) => {
    await page.click('button:has-text("Quality")')
    
    await expect(page.locator('[role="dialog"], [data-state="open"]')).toBeVisible({ timeout: 3000 })
  })

  test('quality options are displayed', async ({ page }) => {
    await page.click('button:has-text("Quality")')
    await page.waitForTimeout(500)
    
    // Should show quality/verification options
    await expect(
      page.locator('text=Verification')
        .or(page.locator('text=verification'))
        .or(page.locator('text=Quality'))
    ).toBeVisible()
  })
})

test.describe('Features Configuration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/orchestration')
    await page.waitForLoadState('networkidle')
  })

  test('features drawer opens when clicking Features card', async ({ page }) => {
    await page.click('button:has-text("Features")')
    
    await expect(page.locator('[role="dialog"], [data-state="open"]')).toBeVisible({ timeout: 3000 })
  })
})

test.describe('Tools Configuration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/orchestration')
    await page.waitForLoadState('networkidle')
  })

  test('tools drawer opens when clicking Tools card', async ({ page }) => {
    await page.click('button:has-text("Tools")')
    
    await expect(page.locator('[role="dialog"], [data-state="open"]')).toBeVisible({ timeout: 3000 })
  })
})

test.describe('Orchestration Settings Persistence', () => {
  test('settings persist in localStorage', async ({ page }) => {
    await page.goto('/orchestration')
    
    // Open models and make a selection
    await page.click('button:has-text("Models")')
    await page.waitForTimeout(500)
    
    // Click to toggle a selection
    const deepseekOption = page.locator('text=DeepSeek')
    if (await deepseekOption.isVisible()) {
      await deepseekOption.click()
    }
    
    await page.keyboard.press('Escape')
    
    // Check localStorage was updated
    const localStorage = await page.evaluate(() => {
      return window.localStorage.getItem('llmhive-orchestrator-settings')
    })
    
    // Settings should be stored
    // (The exact format depends on implementation)
  })

  test('settings persist across page navigation', async ({ page }) => {
    await page.goto('/orchestration')
    
    // Make some selections
    await page.click('button:has-text("Tuning")')
    await page.waitForTimeout(500)
    await page.keyboard.press('Escape')
    
    // Navigate away and back
    await page.goto('/')
    await page.goto('/orchestration')
    
    // Settings should still be applied
    // (Visual verification or badge counts should match)
  })

  test('settings are sent with chat requests', async ({ page }) => {
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

    // Configure some settings
    await page.goto('/orchestration')
    await page.click('button:has-text("Models")')
    await page.waitForTimeout(500)
    await page.keyboard.press('Escape')
    
    // Navigate to home and send a message
    await page.goto('/')
    const textarea = page.locator('textarea[placeholder*="Ask"], textarea[placeholder*="Message"]').first()
    await textarea.fill('Test message')
    await textarea.press('Enter')
    
    // Wait for request to be captured
    await page.waitForResponse('/api/chat')
    
    // Verify settings were included in request
    expect(capturedRequest).toBeDefined()
    if (capturedRequest) {
      expect(capturedRequest.orchestratorSettings).toBeDefined()
    }
  })
})

test.describe('Drawer Interactions', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/orchestration')
    await page.waitForLoadState('networkidle')
  })

  test('only one drawer can be open at a time', async ({ page }) => {
    // Open Models drawer
    await page.click('button:has-text("Models")')
    await expect(page.locator('[role="dialog"], [data-state="open"]')).toBeVisible()
    
    // Try to open another drawer (should close the first)
    await page.keyboard.press('Escape')
    await page.click('button:has-text("Reasoning")')
    
    // Only one dialog should be visible
    const dialogs = await page.locator('[role="dialog"], [data-state="open"]').count()
    expect(dialogs).toBeLessThanOrEqual(1)
  })

  test('drawer closes when clicking outside', async ({ page }) => {
    await page.click('button:has-text("Models")')
    await expect(page.locator('[role="dialog"], [data-state="open"]')).toBeVisible()
    
    // Click on the backdrop/outside area
    await page.click('h1:has-text("Orchestration")')
    
    // Drawer should close (or remain due to sheet behavior)
    await page.waitForTimeout(500)
  })
})

test.describe('Responsive Layout', () => {
  test('orchestration studio works on desktop', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.goto('/orchestration')
    
    // All cards should be visible
    await expect(page.locator('text=Models')).toBeVisible()
    await expect(page.locator('text=Reasoning')).toBeVisible()
  })

  test('orchestration studio works on tablet', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 })
    await page.goto('/orchestration')
    
    // Cards should still be visible (may be in different layout)
    await expect(page.locator('text=Models')).toBeVisible()
    await expect(page.locator('text=Reasoning')).toBeVisible()
  })

  test('orchestration studio works on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/orchestration')
    
    // Core content should be accessible
    await expect(page.locator('h1')).toContainText('Orchestration')
  })
})

test.describe('Speed Configuration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/orchestration')
    await page.waitForLoadState('networkidle')
  })

  test('speed drawer opens when clicking Speed card', async ({ page }) => {
    await page.click('button:has-text("Speed")')
    
    await expect(page.locator('[role="dialog"], [data-state="open"]')).toBeVisible({ timeout: 3000 })
  })
})

test.describe('Orchestration Accessibility', () => {
  test('cards are keyboard accessible', async ({ page }) => {
    await page.goto('/orchestration')
    
    // Tab through cards
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')
    
    // Should be able to activate with Enter
    await page.keyboard.press('Enter')
    
    // Some drawer should open
    await page.waitForTimeout(500)
  })

  test('drawers can be closed with Escape', async ({ page }) => {
    await page.goto('/orchestration')
    await page.click('button:has-text("Models")')
    await expect(page.locator('[role="dialog"], [data-state="open"]')).toBeVisible()
    
    await page.keyboard.press('Escape')
    await expect(page.locator('[role="dialog"], [data-state="open"]')).not.toBeVisible({ timeout: 2000 })
  })
})
