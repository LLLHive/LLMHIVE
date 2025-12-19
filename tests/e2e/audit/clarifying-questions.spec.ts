/**
 * Clarifying Questions Flow Test
 * 
 * Dedicated test to ensure the clarifying questions feature works correctly.
 * This is a critical regression test - DO NOT MODIFY without careful review.
 */

import { test, expect } from '@playwright/test'
import { setupOpenRouterMocks, setupClarifyingQuestionsMock } from './openrouter-mock'

test.describe('Clarifying Questions Flow', () => {
  test.beforeEach(async ({ page }) => {
    await setupOpenRouterMocks(page)
  })

  test('ambiguous query triggers clarifying question', async ({ page }) => {
    // Setup mock that returns clarifying question on first message
    await setupClarifyingQuestionsMock(page)
    
    await page.goto('/', { waitUntil: 'networkidle' })
    
    // Wait for chat to be ready
    const chatInput = page.locator('textarea, input[type="text"]').first()
    await expect(chatInput).toBeVisible({ timeout: 10000 })
    
    // Send ambiguous message
    await chatInput.fill('Tell me about this ambiguous topic that needs clarification')
    await chatInput.press('Enter')
    
    // Wait for response
    await page.waitForTimeout(2000)
    
    // Check for clarifying question elements
    const hasQuestionText = await page.locator('text=/clarification|which aspect|specify/i').first().isVisible().catch(() => false)
    const hasNumberedOptions = await page.locator('text=/^1\\./').first().isVisible().catch(() => false)
    
    // At least one indicator should be present
    expect(hasQuestionText || hasNumberedOptions).toBeTruthy()
  })

  test('answering clarifying question continues flow', async ({ page }) => {
    await setupClarifyingQuestionsMock(page)
    
    await page.goto('/', { waitUntil: 'networkidle' })
    
    const chatInput = page.locator('textarea, input[type="text"]').first()
    await expect(chatInput).toBeVisible({ timeout: 10000 })
    
    // Send ambiguous message
    await chatInput.fill('Tell me about this ambiguous topic')
    await chatInput.press('Enter')
    await page.waitForTimeout(2000)
    
    // Send follow-up answer
    await chatInput.fill('I want option 1 - technical details')
    await chatInput.press('Enter')
    await page.waitForTimeout(2000)
    
    // Should get a full response after answering
    const hasResponse = await page.locator('text=/Thank you|Here is|detailed response/i').first().isVisible().catch(() => false)
    
    // The conversation should have progressed
    expect(hasResponse || await page.locator('.message, [class*="message"]').count() > 2).toBeTruthy()
  })

  test('non-ambiguous query gets direct response', async ({ page }) => {
    // Use standard mock that gives direct response
    await page.route('**/api/chat', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/plain',
        headers: {
          'X-Models-Used': '["gpt-4o"]',
          'X-Tokens-Used': '150',
        },
        body: 'The capital of France is Paris. It is the largest city in France and serves as the country\'s political, economic, and cultural center.',
      })
    })
    
    await page.goto('/', { waitUntil: 'networkidle' })
    
    const chatInput = page.locator('textarea, input[type="text"]').first()
    await expect(chatInput).toBeVisible({ timeout: 10000 })
    
    // Send clear, unambiguous message
    await chatInput.fill('What is the capital of France?')
    await chatInput.press('Enter')
    await page.waitForTimeout(2000)
    
    // Should get direct answer without clarification
    const hasDirectAnswer = await page.locator('text=/Paris/i').first().isVisible().catch(() => false)
    const hasClarification = await page.locator('text=/clarification|which aspect|specify/i').first().isVisible().catch(() => false)
    
    expect(hasDirectAnswer).toBeTruthy()
    expect(hasClarification).toBeFalsy()
  })
})

test.describe('Clarifying Questions UI Elements', () => {
  test.beforeEach(async ({ page }) => {
    await setupOpenRouterMocks(page)
    await setupClarifyingQuestionsMock(page)
  })

  test('clarifying question has proper formatting', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' })
    
    const chatInput = page.locator('textarea, input[type="text"]').first()
    await expect(chatInput).toBeVisible({ timeout: 10000 })
    
    await chatInput.fill('Ambiguous question here')
    await chatInput.press('Enter')
    await page.waitForTimeout(2000)
    
    // Take screenshot of clarifying question
    await page.screenshot({ 
      path: 'docs/ui_audit/reports/latest/screenshots/clarifying_question_ui.png',
      fullPage: true 
    })
    
    // The message area should have content
    const messageArea = page.locator('[class*="message"], [class*="chat"]')
    await expect(messageArea.first()).toBeVisible()
  })

  test('chat input remains functional after clarifying question', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' })
    
    const chatInput = page.locator('textarea, input[type="text"]').first()
    await expect(chatInput).toBeVisible({ timeout: 10000 })
    
    // Send first message
    await chatInput.fill('Ambiguous topic')
    await chatInput.press('Enter')
    await page.waitForTimeout(2000)
    
    // Input should still be usable
    await expect(chatInput).toBeEnabled()
    
    // Should be able to type follow-up
    await chatInput.fill('Follow-up message')
    expect(await chatInput.inputValue()).toBe('Follow-up message')
  })
})

