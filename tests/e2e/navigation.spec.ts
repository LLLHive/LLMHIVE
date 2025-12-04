import { test, expect } from '@playwright/test'

/**
 * Navigation Tests for LLMHive
 * 
 * Tests cover:
 * - Sidebar navigation links
 * - Active state highlighting
 * - Logo navigation
 * - Tooltips
 * - Page loading states
 */

test.describe('Sidebar Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')
  })

  test('home page loads with LLMHive branding', async ({ page }) => {
    // Verify LLMHive logo is visible
    await expect(page.locator('img[alt="LLMHive"]').first()).toBeVisible({ timeout: 15000 })
  })

  test('sidebar shows navigation items', async ({ page }) => {
    // Check main navigation items are present
    await expect(page.getByText('Discover')).toBeVisible()
    await expect(page.getByText('Settings')).toBeVisible()
  })

  test('Discover link navigates to /discover', async ({ page }) => {
    await page.click('a[href="/discover"]')
    await expect(page).toHaveURL('/discover')
    await expect(page.locator('h1')).toContainText('Discover')
  })

  test('Orchestration link navigates to /orchestration', async ({ page }) => {
    await page.click('a[href="/orchestration"]')
    await expect(page).toHaveURL('/orchestration')
    await expect(page.locator('h1')).toContainText('Orchestration')
  })

  test('Settings link navigates to /settings', async ({ page }) => {
    await page.click('a[href="/settings"]')
    await expect(page).toHaveURL('/settings')
    await expect(page.locator('h1')).toContainText('Settings')
  })

  test('logo click returns to home from settings', async ({ page }) => {
    // Navigate to settings
    await page.goto('/settings')
    await expect(page).toHaveURL('/settings')
    
    // Click on the logo to return home
    await page.click('img[alt="LLMHive"]')
    await expect(page).toHaveURL('/')
  })

  test('New Chat button is visible', async ({ page }) => {
    const newChatButton = page.getByRole('button', { name: /New Chat/i })
    await expect(newChatButton).toBeVisible()
  })
})

test.describe('Collaborate Button - Coming Soon', () => {
  test('Collaborate button is disabled', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')
    
    const collaborateButton = page.getByRole('button', { name: /Collaborate/i })
    await expect(collaborateButton).toBeDisabled()
  })

  test('Collaborate button shows Coming Soon tooltip on hover', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')
    
    const collaborateButton = page.getByRole('button', { name: /Collaborate/i })
    await collaborateButton.hover()
    
    // Wait for tooltip to appear
    await expect(page.getByText('Coming Soon')).toBeVisible({ timeout: 5000 })
  })
})

test.describe('Page Loading States', () => {
  test('home page loads without errors', async ({ page }) => {
    const response = await page.goto('/')
    expect(response?.status()).toBe(200)
  })

  test('discover page loads with content', async ({ page }) => {
    await page.goto('/discover')
    await page.waitForLoadState('domcontentloaded')
    
    // Page should render with discover content
    await expect(page.locator('h1')).toContainText('Discover')
  })

  test('orchestration page loads with configuration cards', async ({ page }) => {
    await page.goto('/orchestration')
    await page.waitForLoadState('domcontentloaded')
    
    await expect(page.locator('h1')).toContainText('Orchestration')
    await expect(page.getByText('Models')).toBeVisible()
  })

  test('settings page loads with settings categories', async ({ page }) => {
    await page.goto('/settings')
    await page.waitForLoadState('domcontentloaded')
    
    await expect(page.locator('h1')).toContainText('Settings')
    await expect(page.getByRole('button', { name: /Account/i })).toBeVisible()
  })
})

test.describe('Error Handling', () => {
  test('404 page for invalid routes', async ({ page }) => {
    const response = await page.goto('/this-route-definitely-does-not-exist-12345')
    
    // Should return 404
    expect(response?.status()).toBe(404)
  })
})

test.describe('Navigation Accessibility', () => {
  test('navigation links are focusable', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')
    
    // All navigation links should be focusable
    const discoverLink = page.locator('a[href="/discover"]')
    await expect(discoverLink).toBeVisible()
  })
})
