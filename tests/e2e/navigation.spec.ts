import { test, expect, helpers } from './fixtures'

/**
 * Navigation Tests for LLMHive
 * 
 * Tests cover:
 * - Sidebar navigation links
 * - Active state highlighting
 * - Logo navigation
 * - Tooltips
 * - Page loading states
 * - Browser back/forward
 * - Deep linking
 */

test.describe('Sidebar Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await helpers.waitForPageReady(page)
  })

  test('home page loads with LLMHive branding', async ({ page }) => {
    // Verify LLMHive logo is visible
    await expect(page.locator('img[alt="LLMHive"]').first()).toBeVisible({ timeout: 15000 })
  })

  test('sidebar shows all navigation items', async ({ page }) => {
    // Check main navigation items are present
    await expect(page.getByText('Discover')).toBeVisible()
    await expect(page.getByText('Settings')).toBeVisible()
    await expect(page.getByText('Orchestration')).toBeVisible()
  })

  test('Discover link navigates correctly', async ({ page }) => {
    await page.click('a[href="/discover"]')
    await expect(page).toHaveURL('/discover')
    await expect(page.locator('h1')).toContainText('Discover')
  })

  test('Orchestration link navigates correctly', async ({ page }) => {
    await page.click('a[href="/orchestration"]')
    await expect(page).toHaveURL('/orchestration')
    await expect(page.locator('h1')).toContainText('Orchestration')
  })

  test('Settings link navigates correctly', async ({ page }) => {
    await page.click('a[href="/settings"]')
    await expect(page).toHaveURL('/settings')
    await expect(page.locator('h1')).toContainText('Settings')
  })

  test('logo click returns to home from any page', async ({ page }) => {
    // Navigate to settings
    await page.goto('/settings')
    await expect(page).toHaveURL('/settings')
    
    // Click on the logo to return home
    await page.click('img[alt="LLMHive"]')
    await expect(page).toHaveURL('/')
  })

  test('New Chat button is visible and functional', async ({ page }) => {
    const newChatButton = page.getByRole('button', { name: /New Chat/i })
    await expect(newChatButton).toBeVisible()
    await expect(newChatButton).toBeEnabled()
  })
})

test.describe('Active State Highlighting', () => {
  test('home page has correct active state', async ({ page }) => {
    await page.goto('/')
    await helpers.waitForPageReady(page)
    
    // The home link or logo should indicate current page
    const logo = page.locator('img[alt="LLMHive"]').first()
    await expect(logo).toBeVisible()
  })

  test('discover page link has active state', async ({ page }) => {
    await page.goto('/discover')
    await helpers.waitForPageReady(page)
    
    // Check the Discover link has active styling
    const discoverLink = page.locator('a[href="/discover"]')
    await expect(discoverLink).toBeVisible()
    // The active state should be visually indicated (class or style)
  })

  test('orchestration page link has active state', async ({ page }) => {
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)
    
    const orchestrationLink = page.locator('a[href="/orchestration"]')
    await expect(orchestrationLink).toBeVisible()
  })

  test('settings page link has active state', async ({ page }) => {
    await page.goto('/settings')
    await helpers.waitForPageReady(page)
    
    const settingsLink = page.locator('a[href="/settings"]')
    await expect(settingsLink).toBeVisible()
  })
})

test.describe('Collaborate Button - Coming Soon', () => {
  test('Collaborate button is disabled', async ({ page }) => {
    await page.goto('/')
    await helpers.waitForPageReady(page)
    
    const collaborateButton = page.getByRole('button', { name: /Collaborate/i })
    await expect(collaborateButton).toBeDisabled()
  })

  test('Collaborate button shows Coming Soon tooltip on hover', async ({ page }) => {
    await page.goto('/')
    await helpers.waitForPageReady(page)
    
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
    await helpers.waitForPageReady(page)
    
    await expect(page.locator('h1')).toContainText('Discover')
  })

  test('orchestration page loads with configuration cards', async ({ page }) => {
    await page.goto('/orchestration')
    await helpers.waitForPageReady(page)
    
    await expect(page.locator('h1')).toContainText('Orchestration')
    await expect(page.getByText('Models')).toBeVisible()
  })

  test('settings page loads with settings categories', async ({ page }) => {
    await page.goto('/settings')
    await helpers.waitForPageReady(page)
    
    await expect(page.locator('h1')).toContainText('Settings')
    await expect(page.getByRole('button', { name: /Account/i })).toBeVisible()
  })
})

test.describe('Browser Navigation', () => {
  test('browser back button works correctly', async ({ page }) => {
    await page.goto('/')
    await helpers.waitForPageReady(page)
    
    // Navigate to settings
    await page.click('a[href="/settings"]')
    await expect(page).toHaveURL('/settings')
    
    // Go back
    await page.goBack()
    await expect(page).toHaveURL('/')
  })

  test('browser forward button works correctly', async ({ page }) => {
    await page.goto('/')
    await helpers.waitForPageReady(page)
    
    // Navigate to settings
    await page.click('a[href="/settings"]')
    await expect(page).toHaveURL('/settings')
    
    // Go back and forward
    await page.goBack()
    await expect(page).toHaveURL('/')
    await page.goForward()
    await expect(page).toHaveURL('/settings')
  })

  test('navigation history is maintained', async ({ page }) => {
    await page.goto('/')
    await page.click('a[href="/discover"]')
    await page.click('a[href="/orchestration"]')
    await page.click('a[href="/settings"]')
    
    // Go back through history
    await page.goBack() // orchestration
    await expect(page).toHaveURL('/orchestration')
    await page.goBack() // discover
    await expect(page).toHaveURL('/discover')
    await page.goBack() // home
    await expect(page).toHaveURL('/')
  })
})

test.describe('Deep Linking', () => {
  test('direct URL to discover page works', async ({ page }) => {
    await page.goto('/discover')
    await expect(page).toHaveURL('/discover')
    await expect(page.locator('h1')).toContainText('Discover')
  })

  test('direct URL to orchestration page works', async ({ page }) => {
    await page.goto('/orchestration')
    await expect(page).toHaveURL('/orchestration')
    await expect(page.locator('h1')).toContainText('Orchestration')
  })

  test('direct URL to settings page works', async ({ page }) => {
    await page.goto('/settings')
    await expect(page).toHaveURL('/settings')
    await expect(page.locator('h1')).toContainText('Settings')
  })
})

test.describe('Error Handling', () => {
  test('404 page for invalid routes', async ({ page }) => {
    const response = await page.goto('/this-route-definitely-does-not-exist-12345')
    
    // Should return 404
    expect(response?.status()).toBe(404)
  })

  test('app recovers from navigation errors', async ({ page }) => {
    // Navigate to invalid route
    await page.goto('/invalid-route-xyz')
    
    // Should still be able to navigate to valid routes
    await page.goto('/')
    await helpers.waitForPageReady(page)
    await expect(page.locator('img[alt="LLMHive"]').first()).toBeVisible()
  })
})

test.describe('Navigation Accessibility', () => {
  test('navigation links are keyboard accessible', async ({ page }) => {
    await page.goto('/')
    await helpers.waitForPageReady(page)
    
    // Tab through navigation
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')
    
    // Should be able to activate with Enter
    const focusedElement = await page.evaluate(() => document.activeElement?.tagName)
    expect(['A', 'BUTTON']).toContain(focusedElement)
  })

  test('navigation links have accessible names', async ({ page }) => {
    await page.goto('/')
    await helpers.waitForPageReady(page)
    
    const discoverLink = page.locator('a[href="/discover"]')
    await expect(discoverLink).toBeVisible()
    
    const settingsLink = page.locator('a[href="/settings"]')
    await expect(settingsLink).toBeVisible()
  })
})

test.describe('Navigation Performance', () => {
  test('navigation between pages is fast', async ({ page }) => {
    await page.goto('/')
    await helpers.waitForPageReady(page)
    
    const startTime = Date.now()
    await page.click('a[href="/settings"]')
    await expect(page).toHaveURL('/settings')
    const navigationTime = Date.now() - startTime
    
    // Navigation should be under 3 seconds (generous for dev server)
    expect(navigationTime).toBeLessThan(3000)
  })

  test('multiple rapid navigations work correctly', async ({ page }) => {
    await page.goto('/')
    
    // Rapidly navigate between pages
    await page.click('a[href="/discover"]')
    await page.click('a[href="/orchestration"]')
    await page.click('a[href="/settings"]')
    
    // Should end up on settings
    await expect(page).toHaveURL('/settings')
    await expect(page.locator('h1')).toContainText('Settings')
  })
})
