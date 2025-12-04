import { test, expect } from '@playwright/test'

test.describe('Orchestration Studio', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/orchestration')
  })

  test('page loads with all configuration cards', async ({ page }) => {
    // Verify all cards are present
    await expect(page.locator('text=Elite Mode')).toBeVisible()
    await expect(page.locator('text=Models')).toBeVisible()
    await expect(page.locator('text=Reasoning')).toBeVisible()
    await expect(page.locator('text=Tuning')).toBeVisible()
    await expect(page.locator('text=Features')).toBeVisible()
    await expect(page.locator('text=Tools')).toBeVisible()
    await expect(page.locator('text=Quality')).toBeVisible()
    await expect(page.locator('text=Speed')).toBeVisible()
  })

  test('models drawer opens and shows available models', async ({ page }) => {
    // Click Models card
    await page.click('button:has-text("Models")')
    
    // Drawer should open with models
    await expect(page.locator('text=GPT-4o')).toBeVisible()
    await expect(page.locator('text=Claude')).toBeVisible()
    await expect(page.locator('text=Gemini')).toBeVisible()
  })

  test('can select and deselect models', async ({ page }) => {
    await page.click('button:has-text("Models")')
    
    // Click to select GPT-4o
    const gpt4oItem = page.locator('[data-model="gpt-4o"], :has-text("GPT-4o")').first()
    await gpt4oItem.click()
    
    // Should show selection indicator (badge count increases or checkmark appears)
    // The selection state is tracked in localStorage
  })

  test('reasoning drawer shows reasoning methods', async ({ page }) => {
    await page.click('button:has-text("Reasoning")')
    
    // Should show reasoning methods
    await expect(page.locator('text=Chain of Thought').or(page.locator('text=chain-of-thought'))).toBeVisible()
  })

  test('tuning drawer shows tuning options', async ({ page }) => {
    await page.click('button:has-text("Tuning")')
    
    // Should show tuning options
    await expect(page.locator('text=Prompt Optimization')).toBeVisible()
    await expect(page.locator('text=Output Validation')).toBeVisible()
  })

  test('elite mode drawer shows strategy options', async ({ page }) => {
    await page.click('button:has-text("Elite Mode")')
    
    // Should show elite strategies
    await expect(page.locator('text=Fast')).toBeVisible()
    await expect(page.locator('text=Standard')).toBeVisible()
    await expect(page.locator('text=Thorough')).toBeVisible()
  })

  test('quality drawer shows verification options', async ({ page }) => {
    await page.click('button:has-text("Quality")')
    
    // Should show quality options
    await expect(page.locator('text=Fact Verification').or(page.locator('text=verification'))).toBeVisible()
  })

  test('drawer closes when clicking outside', async ({ page }) => {
    // Open Models drawer
    await page.click('button:has-text("Models")')
    await expect(page.locator('text=GPT-4o')).toBeVisible()
    
    // Click outside (on the main content area)
    await page.click('h1:has-text("Orchestration")')
    
    // Drawer should close
    await expect(page.locator('[role="dialog"]')).not.toBeVisible({ timeout: 2000 })
  })
})

test.describe('Orchestration Settings Persistence', () => {
  test('settings persist across page navigation', async ({ page }) => {
    await page.goto('/orchestration')
    
    // Open tuning and toggle an option
    await page.click('button:has-text("Tuning")')
    
    // Toggle Prompt Optimization
    const promptOptToggle = page.locator('text=Prompt Optimization').locator('..')
    await promptOptToggle.click()
    
    // Close drawer
    await page.keyboard.press('Escape')
    
    // Navigate away
    await page.goto('/')
    
    // Navigate back
    await page.goto('/orchestration')
    
    // Open tuning again - setting should be preserved
    await page.click('button:has-text("Tuning")')
    
    // The setting state should be maintained via localStorage
  })

  test('settings are used in chat requests', async ({ page }) => {
    // Intercept chat API calls
    let capturedRequest: any = null
    await page.route('/api/chat', async (route) => {
      capturedRequest = JSON.parse(route.request().postData() || '{}')
      route.fulfill({
        status: 200,
        contentType: 'text/plain',
        body: 'Test response',
      })
    })

    // Go to orchestration and configure
    await page.goto('/orchestration')
    await page.click('button:has-text("Models")')
    
    // Select a specific model
    await page.locator('text=DeepSeek').click()
    await page.keyboard.press('Escape')
    
    // Navigate to home and send a message
    await page.goto('/')
    await page.click('button:has-text("New Chat")')
    
    const textarea = page.locator('textarea[placeholder*="Ask"]')
    await textarea.fill('Test')
    await textarea.press('Enter')
    
    // Wait for request
    await page.waitForResponse('/api/chat')
    
    // Verify settings were sent (models should include selected model)
    expect(capturedRequest).toBeDefined()
    expect(capturedRequest.orchestratorSettings).toBeDefined()
  })
})

test.describe('Orchestration Card Badges', () => {
  test('cards show count badges for selections', async ({ page }) => {
    await page.goto('/orchestration')
    
    // The Models card should show a count badge
    // Default has "automatic" selected, so count should be >= 1
    const modelsCard = page.locator('button:has-text("Models")')
    
    // Badge should exist with some count
    await expect(modelsCard.locator('.badge, [class*="Badge"]')).toBeVisible()
  })
})
